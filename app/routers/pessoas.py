from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String
from sqlalchemy.exc import IntegrityError
from .. import models
from ..cadastros import backfill_pessoas, chave_principal, sincronizar_chave
from ..database import get_db
from ..models import Pessoa, User, PessoaContato, PessoaChavePix
from ..auth import need
from ..schemas import PessoaIn, PessoaPatch, ContatoIn, ChavePixIn
from ..ordenacao_tabelas import ordenar
from ..audit import audit
from ..importacao_identidade import bloquear_cadastros, validar_documento_novo, documento_normalizado

r = APIRouter(tags=["pessoas"])


def _out(p: Pessoa):
    return {"id": p.id, "tipo": p.tipo, "nome": p.nome, "documento": p.documento,
            "telefone": p.telefone, "email": p.email, "ativo": p.ativo,
            "apelido": p.apelido, "endereco": p.endereco, "chave_pix": p.chave_pix,
            "banco": p.banco, "conta": p.conta, "titular_chave": p.titular_chave,
            "prazo_dias": p.prazo_dias, "tolerancia_credito": p.tolerancia_credito,
            "prioridade": p.prioridade, "observacoes": p.observacoes}


@r.get("/representantes")
def list_rep(ativo: bool | None = None, q: str = "", db: Session = Depends(get_db),
             u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    query = db.query(Pessoa).filter(Pessoa.tipo.in_(["representante", "ambos"]))
    if ativo is not None:
        query = query.filter(Pessoa.ativo == ativo)
    if q:
        query = query.filter(Pessoa.nome.ilike(f"%{q}%"))
    return [_out(p) for p in query.order_by(Pessoa.nome).all()]


@r.post("/representantes", status_code=201)
def create_rep(body: PessoaIn, db: Session = Depends(get_db),
               u: User = Depends(need("admin", "financeiro", "operador"))):
    if body.tipo != "representante":
        raise HTTPException(422, "Use /fornecedores para fornecedor")
    bloquear_cadastros(db)
    validar_documento_novo(db, body.documento)
    p = Pessoa(**body.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    audit(db, u.id, "pessoa_criada", "pessoas", p.id, depois={"nome": p.nome})
    db.commit()
    return {"id": p.id}


@r.get("/fornecedores")
def list_forn(ativo: bool | None = None, q: str = "", db: Session = Depends(get_db),
              u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    query = db.query(Pessoa).filter(Pessoa.tipo.in_(["fornecedor", "ambos"]))
    if ativo is not None:
        query = query.filter(Pessoa.ativo == ativo)
    if q:
        query = query.filter(Pessoa.nome.ilike(f"%{q}%"))
    return [_out(p) for p in query.order_by(Pessoa.nome).all()]


@r.post("/fornecedores", status_code=201)
def create_forn(body: PessoaIn, db: Session = Depends(get_db),
                u: User = Depends(need("admin", "financeiro", "operador"))):
    if body.tipo != "fornecedor":
        raise HTTPException(422, "Use /representantes para representante")
    bloquear_cadastros(db)
    validar_documento_novo(db, body.documento)
    p = Pessoa(**body.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    audit(db, u.id, "pessoa_criada", "pessoas", p.id, depois={"nome": p.nome})
    db.commit()
    return {"id": p.id}



def _pessoa(db, pid):
    p = db.get(Pessoa, pid)
    if not p:
        raise HTTPException(404, "Cadastro não encontrado")
    return p


def _child_out(item):
    return {c.name: getattr(item, c.name) for c in item.__table__.columns}


def _detail(db, p):
    out = _out(p)
    out["contatos"] = [_child_out(c) for c in db.query(PessoaContato).filter_by(pessoa_id=p.id).order_by(PessoaContato.id).all()]
    out["chaves_pix"] = [_child_out(k) for k in db.query(PessoaChavePix).filter_by(pessoa_id=p.id).order_by(PessoaChavePix.id).all()]
    k = chave_principal(db, p)
    out.update(chave_pix=k.chave if k else "", banco=k.banco if k else "",
               conta=k.conta if k else "", titular_chave=k.titular if k else "")
    return out


def _referencias(db, pid, papel=None):
    # Inclui qualquer FK para pessoas: histórico, links, propostas e comprovantes.
    for mapper in models.Base.registry.mappers:
        model = mapper.class_
        for column in mapper.columns:
            if any(fk.target_fullname == "pessoas.id" for fk in column.foreign_keys):
                if model in (PessoaContato, PessoaChavePix):
                    continue
                if model is models.NotaObrigacao and column.name == "pessoa_id":
                    query = db.query(model).filter(model.pessoa_id == pid)
                    if papel:
                        query = query.filter(model.relacao == ("cliente" if papel == "representante" else "fornecedor"))
                    if query.first():
                        return True
                    continue
                if papel == "representante" and column.name not in ("representante_id", "cliente_id"):
                    continue
                if papel == "fornecedor" and "fornecedor" not in column.name:
                    continue
                if db.query(model).filter(getattr(model, column.name) == pid).first():
                    return True
    return False


@r.get("/pessoas")
def list_pessoas(tipo: str | None = None, ativo: bool | None = None, q: str = "",
                 ordenar_por: str | None = None, direcao: str = "asc",
                 db: Session = Depends(get_db),
                 u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    query = db.query(Pessoa)
    if tipo:
        tipo = "representante" if tipo == "cliente" else tipo
        if tipo not in ("representante", "fornecedor", "ambos"):
            raise HTTPException(422, "Tipo inválido")
        query = query.filter(Pessoa.tipo.in_([tipo, "ambos"]))
    if ativo is not None:
        query = query.filter(Pessoa.ativo == ativo)
    if q:
        ids = db.query(PessoaChavePix.pessoa_id).filter(PessoaChavePix.chave.ilike(f"%{q}%"))
        query = query.filter(or_(Pessoa.nome.ilike(f"%{q}%"), Pessoa.apelido.ilike(f"%{q}%"),
                                 cast(Pessoa.id, String).ilike(f"%{q}%"), Pessoa.id.in_(ids),
                                 Pessoa.chave_pix.ilike(f"%{q}%")))
    permitidos = {k: getattr(Pessoa, k) for k in ("nome", "tipo", "documento", "prazo_dias", "ativo")}
    query = ordenar(query, ordenar_por, direcao, permitidos, Pessoa.id, Pessoa.nome.asc())
    return [_detail(db, p) for p in query.all()]


@r.post("/pessoas", status_code=201)
def create_pessoa(body: PessoaIn, db: Session = Depends(get_db),
                  u: User = Depends(need("admin", "financeiro"))):
    bloquear_cadastros(db)
    validar_documento_novo(db, body.documento)
    values = body.model_dump()
    if values["tipo"] == "cliente":
        values["tipo"] = "representante"
    p = Pessoa(**values)
    db.add(p)
    db.flush()
    backfill_pessoas(db, p.id)
    audit(db, u.id, "pessoa_criada", "pessoas", p.id, depois=values)
    db.commit()
    return _detail(db, p)


@r.get("/pessoas/{pid}")
def get_pessoa(pid: int, db: Session = Depends(get_db),
               u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    return _detail(db, _pessoa(db, pid))


@r.patch("/pessoas/{pid}")
def patch_pessoa(pid: int, body: PessoaPatch, db: Session = Depends(get_db),
                 u: User = Depends(need("admin", "financeiro"))):
    bloquear_cadastros(db)
    p = _pessoa(db, pid)
    db.refresh(p)
    if body.documento is not None and documento_normalizado(body.documento) != documento_normalizado(p.documento):
        validar_documento_novo(db, body.documento, pid)
    values = body.model_dump(exclude_unset=True)
    if values.get("tipo") == "cliente":
        values["tipo"] = "representante"
    new_type = values.get("tipo", p.tipo)
    for role in ("representante", "fornecedor"):
        if p.tipo in (role, "ambos") and new_type not in (role, "ambos") and _referencias(db, pid, role):
            raise HTTPException(409, "Papel utilizado no histórico não pode ser removido")
    antes = _out(p)
    backfill_pessoas(db, p.id)
    for field, value in values.items():
        setattr(p, field, value)
    # Escritores legados editam a chave principal, nunca uma alternativa silenciosa.
    if any(k in values for k in ("chave_pix", "banco", "conta", "titular_chave")):
        main = db.query(PessoaChavePix).filter_by(pessoa_id=pid, principal=True).first()
        if main is None and p.chave_pix:
            main = PessoaChavePix(pessoa_id=pid, chave=p.chave_pix, principal=True)
            db.add(main)
        if main:
            for legacy, child in (("chave_pix", "chave"), ("banco", "banco"), ("conta", "conta"), ("titular_chave", "titular")):
                if legacy in values:
                    setattr(main, child, values[legacy])
            if not main.chave:
                main.ativo = main.principal = False
    if any(k in values for k in ("telefone", "email")):
        main_contact = db.query(PessoaContato).filter_by(pessoa_id=pid, principal=True).first()
        if main_contact:
            for field in ("telefone", "email"):
                if field in values:
                    setattr(main_contact, field, values[field])
    db.flush()
    sincronizar_chave(db, p)
    audit(db, u.id, "pessoa_editada", "pessoas", p.id, antes=antes, depois=values)
    db.commit()
    return _detail(db, p)


@r.post("/pessoas/{pid}/desativar")
def desativar(pid: int, db: Session = Depends(get_db), u: User = Depends(need("admin", "financeiro"))):
    bloquear_cadastros(db)
    p = _pessoa(db, pid)
    p.ativo = False
    audit(db, u.id, "pessoa_desativada", "pessoas", pid)
    db.commit()
    return _detail(db, p)


@r.delete("/pessoas/{pid}")
def excluir(pid: int, db: Session = Depends(get_db), u: User = Depends(need("admin", "financeiro"))):
    if _referencias(db, pid):
        raise HTTPException(409, "Cadastro com histórico deve ser desativado")
    return desativar(pid, db, u)


def _save_child(db, u, pid, model, schema, body, cid=None):
    p = _pessoa(db, pid)
    backfill_pessoas(db, p.id)
    item = db.query(model).filter_by(id=cid, pessoa_id=pid).first() if cid else None
    if cid and not item:
        raise HTTPException(404, "Registro não encontrado")
    previous = _child_out(item) if item else None
    values = body if isinstance(body, dict) else body.model_dump()
    if values.get("ativo") is False and "principal" not in values:
        values["principal"] = False
    if item:
        merged = {key: getattr(item, key) for key in schema.model_fields}
        merged.update(values)
        values = schema.model_validate(merged).model_dump()
    if values.get("principal"):
        if not values.get("ativo", True):
            raise HTTPException(422, "Principal precisa estar ativo")
        db.query(model).filter_by(pessoa_id=pid, principal=True).update({"principal": False})
    if item is None:
        item = model(pessoa_id=pid, **values)
        db.add(item)
    else:
        for field, value in values.items():
            setattr(item, field, value)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Outra alteração de principal ocorreu; recarregue o cadastro") from exc
    if model is PessoaChavePix:
        sincronizar_chave(db, p)
    else:
        main = db.query(PessoaContato).filter_by(pessoa_id=pid, principal=True, ativo=True).first()
        p.telefone, p.email = (main.telefone, main.email) if main else ("", "")
    audit(db, u.id, "cadastro_item_editado", model.__tablename__, item.id,
          antes=previous, depois={k: str(v) if hasattr(v, "isoformat") else v for k, v in values.items()})
    db.commit()
    return _child_out(item)


def _register_children(segment, model, schema):
    def create(pid: int, body: schema, db: Session = Depends(get_db), u: User = Depends(need("admin", "financeiro"))):
        return _save_child(db, u, pid, model, schema, body)

    def patch(pid: int, cid: int, body: dict, db: Session = Depends(get_db), u: User = Depends(need("admin", "financeiro"))):
        from pydantic import ValidationError
        try:
            return _save_child(db, u, pid, model, schema, body, cid)
        except ValidationError as exc:
            raise HTTPException(422, str(exc)) from exc

    def deactivate(pid: int, cid: int, db: Session = Depends(get_db), u: User = Depends(need("admin", "financeiro"))):
        return _save_child(db, u, pid, model, schema, {"ativo": False, "principal": False}, cid)

    r.add_api_route(f"/pessoas/{{pid}}/{segment}", create, methods=["POST"], status_code=201)
    r.add_api_route(f"/pessoas/{{pid}}/{segment}/{{cid}}", patch, methods=["PATCH"])
    r.add_api_route(f"/pessoas/{{pid}}/{segment}/{{cid}}", deactivate, methods=["DELETE"])


_register_children("contatos", PessoaContato, ContatoIn)
_register_children("chaves-pix", PessoaChavePix, ChavePixIn)


@r.get("/chave-pix/{fid}")
def chave_pix(fid: int, db: Session = Depends(get_db)):
    from ..ambientes_models import AmbienteOrganizacao
    if db.info.get("runtime_ambiente") and db.query(AmbienteOrganizacao).filter(
            AmbienteOrganizacao.organizacao_id > 1, AmbienteOrganizacao.pronto.is_(True)).first():
        raise HTTPException(404, "Use o link de pagamento da loja")
    p = db.get(Pessoa, fid)
    key = chave_principal(db, p) if p else None
    if not p or p.tipo not in ("fornecedor", "ambos") or not p.ativo or not key:
        raise HTTPException(404, "Chave PIX não encontrada")
    return {"fornecedor_id": p.id, "fornecedor_nome": p.nome,
            "chave_pix": key.chave, "banco": key.banco, "conta": key.conta,
            "titular": key.titular or p.nome}
