"""Cadastro explícito de uma loja isolada; nunca concede acesso à loja original."""
import os
import re
import time
from collections import OrderedDict, deque
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from ..proxy_identity import client_ip
from ..ambientes import provisionar
from ..auth import hash_pw, token_for
from ..database import get_control_db
from ..models import User
from ..organizacoes_models import Organizacao, VinculoOrganizacao

router = APIRouter(prefix='/auth', tags=['cadastro'])
_hits = OrderedDict()
_global_hits = deque()
_lock = Lock()


class CadastroIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    nome: str = Field(min_length=2, max_length=120)
    loja_nome: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=3, max_length=160)
    senha: str = Field(min_length=12, max_length=128)

    @field_validator('nome', 'loja_nome')
    @classmethod
    def nome_limpo(cls, value):
        value = value.strip()
        if len(value) < 2 or any(ord(char) < 32 for char in value):
            raise ValueError('Informe um nome válido')
        return value

    @field_validator('email')
    @classmethod
    def email_valido(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+", value):
            raise ValueError('Informe um email válido')
        return value

    @field_validator('senha')
    @classmethod
    def senha_forte(cls, value):
        if not (any(c.islower() for c in value) and any(c.isupper() for c in value)
                and any(c.isdigit() for c in value) and any(not c.isalnum() and not c.isspace() for c in value)):
            raise ValueError('Use ao menos 12 caracteres, maiúscula, minúscula, número e símbolo')
        return value


def permitir_cadastro(request: Request):
    if os.getenv('REGISTER_PUBLIC_ENABLED', '').lower() != 'true':
        raise HTTPException(403, 'Cadastro indisponível neste ambiente')
    ip = client_ip(request)
    now = time.monotonic()
    with _lock:
        while _global_hits and _global_hits[0] <= now - 3600:
            _global_hits.popleft()
        queue = _hits.setdefault(ip, deque())
        _hits.move_to_end(ip)
        while queue and queue[0] <= now - 3600:
            queue.popleft()
        if len(queue) >= 5 or len(_global_hits) >= 60:
            raise HTTPException(429, 'Muitas tentativas de cadastro. Tente mais tarde.', headers={'Retry-After': '3600'})
        queue.append(now)
        _global_hits.append(now)
        while len(_hits) > 2048:
            _hits.popitem(last=False)


@router.post('/registrar', status_code=201, dependencies=[Depends(permitir_cadastro)])
def registrar(body: CadastroIn, response: Response, db: Session = Depends(get_control_db)):
    response.headers['Cache-Control'] = 'no-store'
    # Serializa consulta e inserção no SQLite, inclusive emails antigos com caixa diferente.
    if db.get_bind().dialect.name == 'sqlite':
        try:
            db.execute(text('BEGIN IMMEDIATE'))
        except OperationalError:
            db.rollback()
            raise HTTPException(409, 'Cadastro em andamento. Tente novamente.')
    try:
        if db.get(Organizacao, 1) is None:
            raise HTTPException(503, 'Ambiente ainda não preparado para cadastro')
        if db.scalar(select(User.id).where(func.lower(func.trim(User.email)) == body.email)):
            raise HTTPException(409, 'Não foi possível cadastrar esse email. Entre com sua conta ou procure o suporte.')
        usuario = User(nome=body.nome, email=body.email, senha_hash=hash_pw(body.senha), perfil='consulta', ativo=False)
        org = Organizacao(nome=body.loja_nome, ativo=False)
        db.add_all([usuario, org])
        db.flush()
        if org.id <= 1:
            raise HTTPException(503, 'Ambiente ainda não preparado para cadastro')
        membro = VinculoOrganizacao(user_id=usuario.id, organizacao_id=org.id, perfil='admin', ativo=False)
        db.add(membro)
        db.flush()
        # Reserva o ID antes de criar arquivos: falhas não permitem reutilizar um banco órfão.
        db.commit()
        # O provisionador confirma a transação; as três entidades continuam inativas até concluir.
        provisionar(db, org, usuario.id)
        usuario.ativo = org.ativo = membro.ativo = True
        db.commit()
        return {'access_token': token_for(usuario, org.id), 'token_type': 'bearer',
                'organizacao_id': org.id,
                'user': {'id': usuario.id, 'nome': usuario.nome, 'email': usuario.email, 'perfil': 'admin'}}
    except HTTPException:
        db.rollback()
        raise
    except (IntegrityError, OperationalError):
        db.rollback()
        raise HTTPException(409, 'Cadastro não concluído. Entre com sua conta ou procure o suporte.')
    except Exception:
        db.rollback()
        raise HTTPException(503, 'Não foi possível preparar sua loja. Procure o suporte.')
