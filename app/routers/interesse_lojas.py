"""Coleta privada para avaliação manual; não provisiona contas nem lojas."""
import re
import time
from collections import OrderedDict, deque
from threading import Lock
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from ..database import get_control_db
from ..interesse_lojas_models import InteresseLoja
from ..proxy_identity import client_ip

router = APIRouter(prefix='/publico', tags=['interesse-lojas'])
_hits = OrderedDict()
_global_hits = deque()
_lock = Lock()
UF = Literal['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']


class InteresseIn(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    nome_contato: str = Field(min_length=2, max_length=120)
    loja_nome: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=3, max_length=160)
    whatsapp: str = Field(min_length=10, max_length=30)
    cidade: str = Field(min_length=2, max_length=120)
    uf: UF
    segmento: Literal['moda', 'cosmeticos', 'utilidades', 'alimentos', 'outro']
    equipe: Literal['1', '2-5', '6-15', '16-50', '51+']
    vendas_pix_mes: Literal['ate-100', '101-500', '501-2000', '2001+', 'nao-sei']
    fornecedores: Literal['1-5', '6-20', '21-50', '51+', 'nenhum']
    modelo_venda: Literal['porta-a-porta', 'loja-fisica', 'online', 'misto']
    controle_atual: Literal['planilha', 'whatsapp', 'sistema', 'papel', 'misto']
    desafio: str = Field(min_length=10, max_length=1000)
    consentimento: Literal[True]

    @field_validator('nome_contato', 'loja_nome', 'cidade', 'desafio')
    @classmethod
    def texto_sem_controles(cls, value):
        if any(ord(char) < 32 and char not in '\n\r\t' for char in value):
            raise ValueError('Informe um texto válido')
        return value

    @field_validator('email')
    @classmethod
    def email_valido(cls, value):
        value = value.lower()
        if not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+", value):
            raise ValueError('Informe um email válido')
        return value

    @field_validator('whatsapp')
    @classmethod
    def telefone_valido(cls, value):
        if not re.fullmatch(r'[+()\d\s.-]+', value):
            raise ValueError('Informe um WhatsApp válido')
        digits = re.sub(r'\D', '', value)
        if len(digits) not in (10, 11, 12, 13) or (len(digits) in (12, 13) and not digits.startswith('55')):
            raise ValueError('Informe o DDD e o número do WhatsApp')
        return digits


def limitar_interesse(request: Request):
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
            raise HTTPException(429, 'Muitas tentativas. Tente novamente em uma hora.', headers={'Retry-After': '3600'})
        queue.append(now)
        _global_hits.append(now)
        while len(_hits) > 2048:
            _hits.popitem(last=False)


@router.post('/interesse-lojas', status_code=201, dependencies=[Depends(limitar_interesse)])
def registrar_interesse(body: InteresseIn, response: Response, db: Session = Depends(get_control_db)):
    response.headers['Cache-Control'] = 'no-store'
    db.add(InteresseLoja(**body.model_dump()))
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(503, 'Não foi possível enviar agora. Tente novamente mais tarde.') from None
    return {'status': 'recebido', 'mensagem': 'Recebemos as informações da sua loja. Nossa equipe avaliará seu perfil e entrará em contato.'}
