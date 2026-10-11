import hashlib
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..ambientes import upload_root
from ..models import Movimentacao, Comprovante, Job, Pessoa, User
from ..auth import need, confere_senha
from ..schemas import MovIn
from ..audit import audit
from ..config import UPLOAD_DIR, MAX_UPLOAD_MB, ALLOWED_EXTS
from ..intelligence import detectar_duplicidades, sugerir_conciliacoes

r = APIRouter(prefix="/movimentacoes", tags=["movimentacoes"])


def _out(m: Movimentacao, alerta: dict | None = None):
    dados = {"id": m.id, "codigo": m.codigo, "data_pix": str(m.data_pix), "valor": m.valor,
             "saldo_disponivel": m.saldo_disponivel, "remetente": m.remetente,
             "representante_id": m.representante_id, "destinatario": m.destinatario,
             "fornecedor_id": m.fornecedor_id, "status": m.status,
             "autor": m.autor, "forma_pagamento": m.forma_pagamento, "natureza": m.natureza,
             "link_token": m.link_token,
             "comprovante": bool(m.comprovante_path), "observacao": m.observacao}
    if alerta:
        dados.update(alerta)
    return dados


def _out_com_alerta(db: Session, m: Movimentacao):
    return _out(m, detectar_duplicidades(db, [m])[m.id])


@r.get("")
def listar(data_ini: str | None = None, data_fim: str | None = None,
           representante_id: int | None = None, fornecedor_id: int | None = None,
           status: str | None = None, q: str = "",
           chave: str = "", com_link: bool | None = None,
           limit: int = 100, offset: int = 0,
           db: Session = Depends(get_db),
           u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    limit = min(max(limit, 1), 500)
    query = db.query(Movimentacao).order_by(Movimentacao.id.desc())
    if data_ini:
        query = query.filter(Movimentacao.data_pix >= data_ini)
    if data_fim:
        query = query.filter(Movimentacao.data_pix <= data_fim)
    if representante_id:
        query = query.filter(Movimentacao.representante_id == representante_id)
    if fornecedor_id:
        query = query.filter(Movimentacao.fornecedor_id == fornecedor_id)
    if status:
        query = query.filter(Movimentacao.status == status)
    if q:
        like = f"%{q}%"
        query = query.filter((Movimentacao.codigo.ilike(like)) |
                             (Movimentacao.remetente.ilike(like)) |
                             (Movimentacao.destinatario.ilike(like)))
    if chave:
        like = f"%{chave}%"
        query = query.outerjoin(Pessoa, Pessoa.id == Movimentacao.fornecedor_id).filter(
            (Movimentacao.remetente.ilike(like)) |
            (Movimentacao.destinatario.ilike(like)) |
            (Pessoa.chave_pix.ilike(like)))
    if com_link is True:
        query = query.filter(Movimentacao.link_token != "")
    elif com_link is False:
        query = query.filter(Movimentacao.link_token == "")
    rows = query.offset(offset).limit(limit).all()
    alertas = detectar_duplicidades(db, rows)
    return [_out(m, alertas[m.id]) for m in rows]


@r.get("/{mid}")
def detalhar(mid: int, db: Session = Depends(get_db),
             u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    m = db.get(Movimentacao, mid)
    if not m:
        raise HTTPException(404, "Não encontrada")
    return _out_com_alerta(db, m)


@r.get("/{mid}/sugestoes")
def sugestoes(mid: int, db: Session = Depends(get_db),
              u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    m = db.get(Movimentacao, mid)
    if not m:
        raise HTTPException(404, "Não encontrada")
    return {"movimentacao_id": m.id,
            "saldo_disponivel": round(float(m.saldo_disponivel), 2),
            "sugestoes": sugerir_conciliacoes(db, m),
            "aviso": "Sugestões informativas; revise antes de conciliar."}


@r.post("", status_code=201)
def criar(body: MovIn, db: Session = Depends(get_db),
          u: User = Depends(need("admin", "financeiro", "operador"))):
    # código derivado do id pós-flush: sem race de count()+1 (Risco 3)
    m = Movimentacao(codigo="PIX-TMP", data_pix=body.data_pix, valor=body.valor,
                     saldo_disponivel=body.valor, remetente=body.remetente,
                     representante_id=body.representante_id, destinatario=body.destinatario,
                     fornecedor_id=body.fornecedor_id, observacao=body.observacao,
                     autor=body.autor, forma_pagamento=body.forma_pagamento or "PIX",
                     natureza=body.natureza or "DESPESA", link_token=body.link_token or "",
                     status="disponivel", created_by=u.id)
    db.add(m)
    db.flush()
    m.codigo = f"PIX-{m.id:06d}"
    db.flush()
    audit(db, u.id, "movimentacao_criada", "movimentacoes", m.id,
          depois={"codigo": m.codigo, "valor": m.valor})
    db.commit()
    db.refresh(m)
    return _out_com_alerta(db, m)


@r.patch("/{mid}")
def editar(mid: int, body: dict, db: Session = Depends(get_db),
           u: User = Depends(need("admin", "financeiro"))):
    m = db.get(Movimentacao, mid)
    if not m:
        raise HTTPException(404, "Não encontrada")
    if m.status == "conciliada":
        raise HTTPException(422, "Movimentação conciliada: use estorno, não edição direta")
    antes = _out(m)
    for k in ("remetente", "destinatario", "observacao", "representante_id", "fornecedor_id", "data_pix",
              "autor", "forma_pagamento", "natureza"):
        if k in body:
            setattr(m, k, body[k])
    audit(db, u.id, "movimentacao_editada", "movimentacoes", m.id, antes=antes, depois=body)
    db.commit()
    return _out_com_alerta(db, m)


@r.post("/{mid}/cancelar")
def cancelar(mid: int, body: dict, db: Session = Depends(get_db),
             u: User = Depends(need("admin", "financeiro"))):
    """Exclusão lógica — RN-004: nunca some do histórico."""
    confere_senha(u, body.get("senha"))
    m = db.get(Movimentacao, mid)
    if not m:
        raise HTTPException(404, "Não encontrada")
    if m.status == "conciliada" or m.saldo_disponivel != m.valor:
        raise HTTPException(422, "Movimentação com conciliação: estorne antes de cancelar")
    m.status = "cancelada"
    audit(db, u.id, "movimentacao_excluida", "movimentacoes", m.id)
    db.commit()
    return _out_com_alerta(db, m)


@r.post("/{mid}/comprovante")
def anexar(mid: int, f: UploadFile = File(...), db: Session = Depends(get_db),
           u: User = Depends(need("admin", "financeiro", "operador"))):
    m = db.get(Movimentacao, mid)
    if not m:
        raise HTTPException(404, "Não encontrada")
    ext = os.path.splitext(f.filename or "")[1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(422, f"Extensão inválida. Use {sorted(ALLOWED_EXTS)}")
    data = f.file.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(422, f"Arquivo maior que {MAX_UPLOAD_MB}MB")
    digest = hashlib.sha256(data).hexdigest()
    dup = db.query(Comprovante).filter_by(arquivo_hash=digest).first()
    if dup:
        raise HTTPException(422, f"Comprovante duplicado (já usado no id={dup.id})")
    d = os.path.join(upload_root(db, base=UPLOAD_DIR), str(mid))
    os.makedirs(d, exist_ok=True)
    if Path(d).resolve() != Path(d):
        raise HTTPException(503, "Diretório de arquivos indisponível")
    # nome único por conteúdo: segundo upload nunca sobrescreve o primeiro
    path = os.path.join(d, f"comprovante-{digest[:12]}{ext}")
    if Path(path).resolve() != Path(path):
        raise HTTPException(503, "Arquivo indisponível")
    with open(path, "wb") as fh:
        fh.write(data)
    m.comprovante_path = path
    comp = Comprovante(movimentacao_id=m.id, arquivo_path=path, arquivo_hash=digest,
                       origem="upload", enviado_por=u.nome, etapa="registrado",
                       created_by=u.id)
    db.add(comp)
    db.flush()
    db.add(Job(tipo="comprovante", ref_id=comp.id, status="pendente"))
    audit(db, u.id, "comprovante_anexado", "movimentacoes", m.id, depois={"path": path})
    db.commit()
    return {"ok": True, "path": path, "comprovante_id": comp.id}


@r.get("/{mid}/comprovantes")
def listar_comp(mid: int, db: Session = Depends(get_db),
                u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    rows = db.query(Comprovante).filter_by(movimentacao_id=mid).order_by(Comprovante.id).all()
    return [{"id": c.id, "origem": c.origem, "enviado_por": c.enviado_por,
             "data_comprovante": str(c.data_comprovante) if c.data_comprovante else None,
             "etapa": c.etapa, "extraido": c.extraido_json,
             "sugestao_fornecedor_id": c.sugestao_fornecedor_id,
             "sugestao_motivo": c.sugestao_motivo,
             "sugestao_status": c.sugestao_status} for c in rows]


@r.patch("/comprovantes/{cid}")
def etapa_comp(cid: int, body: dict, db: Session = Depends(get_db),
               u: User = Depends(need("admin", "financeiro"))):
    c = db.get(Comprovante, cid)
    if not c:
        raise HTTPException(404, "Não encontrado")
    if "etapa" in body:
        if body["etapa"] not in ("recebido", "registrado"):
            raise HTTPException(422, "Etapa inválida (recebido|registrado)")
        c.etapa = body["etapa"]
    for k in ("enviado_por", "data_comprovante"):
        if k in body:
            setattr(c, k, body[k])
    audit(db, u.id, "comprovante_atualizado", "comprovantes", c.id, depois=body)
    db.commit()
    return {"id": c.id, "etapa": c.etapa}


@r.get("/revisao/fila")
def fila_revisao(db: Session = Depends(get_db),
                 u: User = Depends(need("admin", "financeiro", "operador"))):
    """Sprint C: comprovantes com extração + sugestão pendente de revisão."""
    rows = db.query(Comprovante).filter(
        Comprovante.extraido_json != "",
        Comprovante.sugestao_status == "pendente").order_by(Comprovante.id).all()
    out = []
    for c in rows:
        m = db.get(Movimentacao, c.movimentacao_id)
        fn = db.get(Pessoa, c.sugestao_fornecedor_id)
        out.append({"comprovante_id": c.id, "movimentacao_id": c.movimentacao_id,
                    "codigo": m.codigo if m else "?", "valor": m.valor if m else 0,
                    "autor": m.autor if m else "", "remetente": m.remetente if m else "",
                    "data_pix": str(m.data_pix) if m else "",
                    "fornecedor_atual_id": m.fornecedor_id if m else None,
                    "sugestao_fornecedor_id": c.sugestao_fornecedor_id,
                    "sugestao_fornecedor_nome": fn.nome if fn else "?",
                    "sugestao_motivo": c.sugestao_motivo})
    return out


@r.post("/comprovantes/{cid}/sugestao")
def decidir_sugestao(cid: int, body: dict, db: Session = Depends(get_db),
                     u: User = Depends(need("admin", "financeiro", "operador"))):
    """Aceitar aplica o fornecedor sugerido (se a mov ainda permite edição);
    rejeitar só registra. Nunca concilia sozinho."""
    c = db.get(Comprovante, cid)
    if not c or c.sugestao_status != "pendente":
        raise HTTPException(404, "Sugestão não encontrada ou já decidida")
    acao = body.get("acao")
    if acao not in ("aceitar", "rejeitar"):
        raise HTTPException(422, "acao deve ser aceitar|rejeitar")
    if acao == "aceitar":
        m = db.get(Movimentacao, c.movimentacao_id)
        if m and m.status != "conciliada" and c.sugestao_fornecedor_id:
            m.fornecedor_id = c.sugestao_fornecedor_id
        c.sugestao_status = "aceita"
    else:
        c.sugestao_status = "rejeitada"
    audit(db, u.id, "sugestao_decidida", "comprovantes", c.id, depois={"acao": acao})
    db.commit()
    return {"id": c.id, "sugestao_status": c.sugestao_status}


@r.get("/{mid}/comprovante")
def baixar(mid: int, db: Session = Depends(get_db),
           u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    m = db.get(Movimentacao, mid)
    if not m or not m.comprovante_path or not os.path.exists(m.comprovante_path):
        raise HTTPException(404, "Comprovante não encontrado")
    path = Path(m.comprovante_path).resolve()
    root = upload_root(db, base=UPLOAD_DIR)
    if (not path.is_relative_to(root)
            or (db.info.get("organizacao_id", 1) == 1 and path.is_relative_to(root / "organizacoes"))):
        raise HTTPException(404, "Comprovante não encontrado")
    return FileResponse(path, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
