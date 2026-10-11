"""Catálogos administrativos e preferências privadas por usuário/tela."""
import json
from decimal import Decimal, InvalidOperation
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..auth import need
from ..audit import audit
from ..database import get_db
from ..models import CatalogoConfig, PreferenciaTabela
from ..referencias_financeiras import bloquear_referencia
from ..configuracoes_schemas import CatalogoIn, CatalogoPatch, PreferenciaIn, COLUNAS, ORDENAVEIS, FILTROS

r = APIRouter(prefix="/configuracoes", tags=["configuracoes"])
Tipo = Literal["formas", "operacoes", "condicoes"]
Tela = Literal["cadastros", "notas", "pagamentos"]
LEITURA = need("admin", "financeiro", "operador", "consulta")
ESCRITA = need("admin", "financeiro")


def _out(item):
    return {k: getattr(item, k) for k in ("id", "tipo", "nome", "ativo", "forma_base", "aplicavel_em", "prazo_dias", "version")}


def _item(db, tipo, cid):
    item = db.get(CatalogoConfig, cid)
    if not item or item.tipo != tipo:
        raise HTTPException(404, "Item não encontrado neste catálogo")
    return item


def _commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Nome já utilizado neste catálogo")


@r.get("/catalogos/{tipo}")
def listar(tipo: Tipo, ativo: bool | None = None, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db), u=Depends(LEITURA)):
    q = db.query(CatalogoConfig).filter_by(tipo=tipo)
    if ativo is not None: q = q.filter(CatalogoConfig.ativo == ativo)
    total = q.count()
    items = [_out(i) for i in q.order_by(CatalogoConfig.nome, CatalogoConfig.id).offset(offset).limit(limit).all()]
    return {"itens": items, "total": total, "limit": limit, "offset": offset, "tem_mais": offset + len(items) < total}


@r.post("/catalogos/{tipo}", status_code=201)
def criar(tipo: Tipo, body: CatalogoIn, db: Session = Depends(get_db), u=Depends(ESCRITA)):
    values = body.model_dump()
    if tipo == "formas":
        if body.forma_base is None or body.prazo_dias is not None or body.aplicavel_em not in (None, "pagamentos"):
            raise HTTPException(422, "Forma exige base PIX/dinheiro e aplicação somente em pagamentos")
        values["aplicavel_em"] = "pagamentos"
    elif tipo == "condicoes":
        if body.prazo_dias is None or body.forma_base is not None or body.aplicavel_em not in (None, "notas"):
            raise HTTPException(422, "Condição exige prazo em dias e aplicação somente em notas")
        values["aplicavel_em"] = "notas"
    else:
        if body.forma_base is not None or body.prazo_dias is not None:
            raise HTTPException(422, "Operação é descritiva, sem forma ou prazo financeiro")
        values["aplicavel_em"] = body.aplicavel_em or "ambos"
    bloquear_referencia(db, "mutex:catalogos")
    item = CatalogoConfig(**values, tipo=tipo, nome_chave=body.nome.casefold(), created_by=u.id)
    db.add(item)
    try: db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Nome já utilizado neste catálogo")
    audit(db, u.id, "catalogo_criado", item.__tablename__, item.id, depois=_out(item))
    _commit(db)
    return _out(item)


@r.get("/catalogos/{tipo}/{cid}")
def detalhe(tipo: Tipo, cid: int, db: Session = Depends(get_db), u=Depends(LEITURA)):
    return _out(_item(db, tipo, cid))


@r.patch("/catalogos/{tipo}/{cid}")
def editar(tipo: Tipo, cid: int, body: CatalogoPatch, db: Session = Depends(get_db), u=Depends(ESCRITA)):
    if any(value is None for value in body.model_dump(exclude_unset=True).values()):
        raise HTTPException(422, "Nome e ativo não podem ser nulos")
    bloquear_referencia(db, "mutex:catalogos")
    item = _item(db, tipo, cid)
    db.refresh(item)
    before = _out(item)
    for field, value in body.model_dump(exclude_unset=True).items(): setattr(item, field, value)
    item.nome_chave = item.nome.casefold()
    item.version += 1
    audit(db, u.id, "catalogo_editado", item.__tablename__, item.id, antes=before, depois=_out(item))
    _commit(db)
    return _out(item)


@r.post("/catalogos/{tipo}/{cid}/desativar")
def desativar(tipo: Tipo, cid: int, db: Session = Depends(get_db), u=Depends(ESCRITA)):
    return editar(tipo, cid, CatalogoPatch(ativo=False), db, u)


def _default(tela):
    return {"colunas": [{"campo": c, "visivel": True} for c in COLUNAS[tela]], "ordenacao": None, "filtros": {}}


def _validar(tela, body):
    fields = [c.campo for c in body.colunas]
    if len(fields) != len(set(fields)) or set(fields) != set(COLUNAS[tela]):
        raise HTTPException(422, "Informe cada coluna permitida exatamente uma vez")
    if not next(c.visivel for c in body.colunas if c.campo == COLUNAS[tela][0]):
        raise HTTPException(422, "Coluna de identificação deve permanecer visível")
    if body.ordenacao and body.ordenacao.campo not in ORDENAVEIS[tela]:
        raise HTTPException(422, "Campo de ordenação inválido")
    if not set(body.filtros) <= FILTROS[tela]:
        raise HTTPException(422, "Filtro não permitido nesta tabela")
    enums = {"tipo": {"cliente", "representante", "fornecedor", "ambos"} if tela == "cadastros" else {"cliente_loja", "cliente_fornecedor", "repasse_fornecedor"},
        "relacao": {"cliente", "fornecedor"}, "status": {"aberto", "parcial", "quitado", "cancelado"}, "forma": {"PIX", "dinheiro"}, "origem_registro": {"manual", "nao_informada"}}
    money = {}
    for k, v in body.filtros.items():
        if k in ("valor_min", "valor_max"):
            try:
                if type(v) not in (int, float, str): raise ValueError()
                dec = Decimal(str(v))
                if not dec.is_finite() or dec < 0 or dec > Decimal("9999999999.99") or dec * 100 != (dec * 100).to_integral_value(): raise ValueError()
                money[k] = dec
            except (InvalidOperation, ValueError):
                raise HTTPException(422, "Filtro monetário inválido; use valor finito com até duas casas decimais")
        if k.endswith("_id") and (type(v) is not int or v <= 0): raise HTTPException(422, "Identificador de filtro inválido")
        if k in ("ativo", "em_atraso") and type(v) is not bool: raise HTTPException(422, "Filtro deve ser booleano")
        if k == "q" and (not isinstance(v, str) or len(v) > 160): raise HTTPException(422, "Busca inválida")
        if k in enums and (not isinstance(v, str) or v not in enums[k]): raise HTTPException(422, "Valor de filtro inválido")

    if "valor_min" in money and "valor_max" in money and money["valor_min"] > money["valor_max"]:
        raise HTTPException(422, "Valor máximo não pode ser menor que o mínimo")


@r.get("/tabelas/{tela}")
def preferencias(tela: Tela, response: Response, db: Session = Depends(get_db), u=Depends(LEITURA)):
    response.headers["Cache-Control"] = "private, no-store"
    item = db.query(PreferenciaTabela).filter_by(user_id=u.id, tela=tela).first()
    return json.loads(item.configuracao_json) if item else _default(tela)


@r.put("/tabelas/{tela}")
def salvar(tela: Tela, body: PreferenciaIn, response: Response, db: Session = Depends(get_db), u=Depends(LEITURA)):
    response.headers["Cache-Control"] = "private, no-store"
    _validar(tela, body)
    dialect = db.get_bind().dialect.name
    if dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    elif dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else: raise HTTPException(503, "Banco não suportado")
    encoded = json.dumps(body.model_dump(), ensure_ascii=False)
    statement = insert(PreferenciaTabela).values(user_id=u.id, tela=tela, configuracao_json=encoded)
    db.execute(statement.on_conflict_do_update(index_elements=["user_id", "tela"], set_={"configuracao_json": encoded}))
    audit(db, u.id, "preferencia_tabela_salva", "preferencias_tabelas", None, depois={"tela": tela})
    db.commit()
    return body.model_dump()


@r.delete("/tabelas/{tela}")
def reset(tela: Tela, response: Response, db: Session = Depends(get_db), u=Depends(LEITURA)):
    response.headers["Cache-Control"] = "private, no-store"
    db.query(PreferenciaTabela).filter_by(user_id=u.id, tela=tela).delete()
    audit(db, u.id, "preferencia_tabela_resetada", "preferencias_tabelas", None, depois={"tela": tela})
    db.commit()
    return _default(tela)
