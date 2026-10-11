"""Notas com abatimentos documentais e aplicações de pagamentos novos; legado separado."""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import re
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy import update, func, case, and_
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlalchemy.orm import Session
from ..database import get_db
from ..ambientes import upload_root
from ..models import Pessoa, User, NotaObrigacao, NotaAbatimento, NotaAbatimentoEstorno, NotaAnexo, Pagamento, PagamentoAplicacao, CreditoConta, CreditoAplicacao
from ..auth import need, confere_senha
from ..audit import audit
from ..cadastros import hoje
from ..config import UPLOAD_DIR, MAX_UPLOAD_MB
from ..catalogos import resolver_catalogos
from ..ordenacao_tabelas import ordenar
from ..notas_schemas import NotaIn, AbatimentoIn, DesfazerIn
from ..referencias_financeiras import bloquear_referencia, chave_referencia

r = APIRouter(tags=["notas"])
LEITURA = need("admin", "financeiro", "operador", "consulta")
ESCRITA = need("admin", "financeiro")


def _nota(db, nid):
    n = db.get(NotaObrigacao, nid)
    if not n:
        raise HTTPException(404, "Nota não encontrada")
    return n


def _total(db, nid):
    return round(float(db.query(func.coalesce(func.sum(NotaAbatimento.valor), 0)).filter_by(
        nota_id=nid, estornado=False).scalar()), 2)


def _out(db, n, abatido=None, pessoa_nome=None):
    abatido = _total(db, n.id) if abatido is None else round(float(abatido), 2)
    saldo = round(n.valor_original - abatido, 2)
    status = "cancelado" if n.cancelada else "quitado" if saldo == 0 else "parcial" if abatido else "aberto"
    return {"condicao_id": n.condicao_id, "condicao_nome_snapshot": n.condicao_nome_snapshot,
            "operacao_id": n.operacao_id, "operacao_nome_snapshot": n.operacao_nome_snapshot,
            "id": n.id, "pessoa_id": n.pessoa_id, "pessoa_nome": pessoa_nome if pessoa_nome is not None else db.get(Pessoa, n.pessoa_id).nome,
            "relacao": n.relacao, "operacao": "venda" if n.relacao == "cliente" else "compra",
            "numero_documento": n.numero_documento, "valor_original": n.valor_original,
            "valor_abatido": abatido, "saldo_aberto": saldo, "status": status,
            "em_atraso": not n.cancelada and saldo > 0 and n.vencimento is not None and n.vencimento < hoje(),
            "data_emissao": n.data_emissao, "vencimento": n.vencimento,
            "modo_vencimento": n.modo_vencimento, "prazo_dias_snapshot": n.prazo_dias_snapshot,
            "descricao": n.descricao, "motivo_cancelamento": n.motivo_cancelamento,
            "created_at": n.created_at}


def _abatimento_out(db, a):
    e = db.query(NotaAbatimentoEstorno).filter_by(abatimento_id=a.id).first()
    return {"id": a.id, "nota_id": a.nota_id, "valor": a.valor, "data": a.data,
            "referencia": a.referencia, "observacao": a.observacao, "origem": a.origem,
            "chave_idempotencia": a.chave_idempotencia, "estornado": a.estornado,
            "credito_aplicacao_id": a.credito_aplicacao_id,
            "credito_id": db.get(CreditoAplicacao, a.credito_aplicacao_id).credito_id if a.credito_aplicacao_id else None,
            "pagamento_aplicacao_id": a.pagamento_aplicacao_id,
            "pagamento_id": db.get(PagamentoAplicacao, a.pagamento_aplicacao_id).pagamento_id if a.pagamento_aplicacao_id else None,
            "acerto_id": db.get(PagamentoAplicacao, a.pagamento_aplicacao_id).acerto_id if a.pagamento_aplicacao_id else db.get(CreditoAplicacao, a.credito_aplicacao_id).acerto_id if a.credito_aplicacao_id else None,
            "created_by": a.created_by, "created_at": a.created_at,
            "estorno": {"id": e.id, "motivo": e.motivo, "created_by": e.created_by,
                         "created_at": e.created_at} if e else None}


def _anexo_out(a):
    return {"id": a.id, "nota_id": a.nota_id, "nome_original": a.nome_original,
            "tamanho": a.tamanho, "ativo": a.ativo, "created_at": a.created_at,
            "url_download": f"/notas/{a.nota_id}/anexos/{a.id}/arquivo"}


def _cas(db, n):
    """UPDATE retém lock do banco até commit; versão protege leituras antigas."""
    try:
        res = db.execute(update(NotaObrigacao).where(NotaObrigacao.id == n.id,
            NotaObrigacao.version == n.version).values(version=n.version + 1),
            execution_options={"synchronize_session": False})
    except OperationalError:
        db.rollback()
        raise HTTPException(409, "Nota em atualização. Recarregue e tente novamente")
    if res.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Nota alterada em outra sessão. Recarregue")


def _consulta_notas(db):
    abat = db.query(NotaAbatimento.nota_id.label("nid"),
        func.sum(NotaAbatimento.valor).label("abatido")).filter_by(estornado=False).group_by(NotaAbatimento.nota_id).subquery()
    total = func.coalesce(abat.c.abatido, 0)
    # SQLite calcula NUMERIC com ponto flutuante; filtros devem usar os
    # mesmos centavos apresentados no detalhe (0,30 - 0,10 - 0,20 = zero).
    saldo = func.round(NotaObrigacao.valor_original - total, 2)
    estado = case((NotaObrigacao.cancelada == True, "cancelado"), (saldo == 0, "quitado"),
                  (total > 0, "parcial"), else_="aberto")
    atraso = and_(NotaObrigacao.cancelada == False, saldo > 0,
                  NotaObrigacao.vencimento.isnot(None), NotaObrigacao.vencimento < hoje())
    q = db.query(NotaObrigacao, total, Pessoa.nome).outerjoin(abat, abat.c.nid == NotaObrigacao.id).join(Pessoa, Pessoa.id == NotaObrigacao.pessoa_id)
    return q, estado, atraso


@r.get("/notas")
def listar(pessoa_id: int | None = None, relacao: str | None = None,
           status: str | None = None, em_atraso: bool | None = None,
           limit: int = 100, offset: int = 0, ordenar_por: str | None = None, direcao: str = "asc", db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    if relacao and relacao not in ("cliente", "fornecedor"):
        raise HTTPException(422, "Relação inválida")
    if status and status not in ("aberto", "parcial", "quitado", "cancelado"):
        raise HTTPException(422, "Status inválido")
    q, estado, atraso = _consulta_notas(db)
    if pessoa_id:
        q = q.filter(NotaObrigacao.pessoa_id == pessoa_id)
    if relacao:
        q = q.filter(NotaObrigacao.relacao == relacao)
    if status:
        q = q.filter(estado == status)
    if em_atraso is not None:
        q = q.filter(atraso if em_atraso else ~atraso)
    total_expr = q.column_descriptions[1]["expr"]
    permitidos = {k: getattr(NotaObrigacao, k) for k in ("numero_documento", "relacao", "valor_original", "data_emissao", "vencimento")}
    permitidos.update(pessoa_nome=Pessoa.nome, status=estado, valor_abatido=total_expr, saldo_aberto=func.round(NotaObrigacao.valor_original - total_expr, 2))
    q = ordenar(q, ordenar_por, direcao, permitidos, NotaObrigacao.id, NotaObrigacao.id.desc())
    rows = q.offset(max(offset, 0)).limit(min(max(limit, 1), 500)).all()
    return [_out(db, n, total, nome) for n, total, nome in rows]


@r.post("/notas", status_code=201)
def criar(body: NotaIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    p = db.get(Pessoa, body.pessoa_id)
    role = "representante" if body.relacao == "cliente" else "fornecedor"
    if not p or not p.ativo or p.tipo not in (role, "ambos"):
        raise HTTPException(422, "Cadastro ativo com o papel da relação é obrigatório")
    meta = resolver_catalogos(db, "notas", operacao_id=body.operacao_id, condicao_id=body.condicao_id)
    prazo = meta.get("prazo_dias_snapshot", p.prazo_dias if body.modo_vencimento == "prazo_cadastro" else body.prazo_dias)
    vencimento = body.vencimento
    if body.modo_vencimento in ("prazo_cadastro", "prazo_informado"):
        if prazo is None or not 0 <= prazo <= 36500:
            raise HTTPException(422, "Prazo do cadastro inválido")
        try:
            vencimento = body.data_emissao + timedelta(days=prazo)
        except OverflowError:
            raise HTTPException(422, "Prazo excede o limite da data")
    n = NotaObrigacao(pessoa_id=p.id, relacao=body.relacao, numero_documento=body.numero_documento,
        valor_original=float(body.valor_original), data_emissao=body.data_emissao,
        vencimento=vencimento, prazo_dias_snapshot=prazo, modo_vencimento="prazo_informado" if body.condicao_id else body.modo_vencimento,
        descricao=body.descricao, created_by=u.id,
        condicao_id=body.condicao_id, condicao_nome_snapshot=meta.get("condicao_nome_snapshot"),
        operacao_id=body.operacao_id, operacao_nome_snapshot=meta.get("operacao_nome_snapshot"))
    db.add(n)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Número de documento já cadastrado nesta pessoa e relação")
    audit(db, u.id, "nota_criada", "notas_obrigacoes", n.id, depois=body.model_dump())
    db.commit()
    return _out(db, n)


@r.get("/pessoas/{pid}/extrato-notas")
def extrato(pid: int, relacao: str, db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    p = db.get(Pessoa, pid)
    if not p:
        raise HTTPException(404, "Cadastro não encontrado")
    if relacao not in ("cliente", "fornecedor"):
        raise HTTPException(422, "Relação inválida")
    q, _, _ = _consulta_notas(db)
    rows = [_out(db, n, total, nome) for n, total, nome in q.filter(NotaObrigacao.pessoa_id == pid, NotaObrigacao.relacao == relacao)
            .order_by(NotaObrigacao.data_emissao, NotaObrigacao.id).all()]
    ativas = [n for n in rows if n["status"] != "cancelado"]
    resumo = {k: round(sum(n[k] for n in ativas), 2) for k in ("valor_original", "valor_abatido", "saldo_aberto")}
    resumo["saldo_vencido"] = round(sum(n["saldo_aberto"] for n in ativas if n["em_atraso"]), 2)
    return {"pessoa_id": pid, "pessoa_nome": p.nome, "relacao": relacao,
            "origem": "notas_rotapay", "resumo": resumo, "notas": rows}


@r.get("/notas/{nid}")
def detalhe(nid: int, db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    out = _out(db, _nota(db, nid))
    out["abatimentos"] = [_abatimento_out(db, a) for a in db.query(NotaAbatimento).filter_by(nota_id=nid).order_by(NotaAbatimento.id)]
    out["anexos"] = [_anexo_out(a) for a in db.query(NotaAnexo).filter_by(nota_id=nid, ativo=True).order_by(NotaAnexo.id)]
    return out


@r.post("/notas/{nid}/abatimentos", status_code=201)
def abater(nid: int, body: AbatimentoIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    n = _nota(db, nid)
    anterior = db.query(NotaAbatimento).filter_by(nota_id=nid, chave_idempotencia=body.chave_idempotencia).first()
    if anterior:
        igual = (Decimal(str(anterior.valor)) == body.valor and anterior.data == body.data
                 and anterior.referencia == body.referencia and anterior.observacao == body.observacao)
        if not igual:
            raise HTTPException(409, "Chave de requisição já usada com dados diferentes")
        return _abatimento_out(db, anterior)
    ref = bloquear_referencia(db, body.referencia)
    if db.query(Pagamento.id).filter(Pagamento.referencia_chave == ref).first() or db.query(CreditoConta.id).filter(CreditoConta.referencia_chave == ref).first() or db.query(NotaAbatimento.id).filter(
        NotaAbatimento.origem.in_(("pagamento", "credito")), NotaAbatimento.referencia_chave == ref).first():
        db.rollback()
        raise HTTPException(409, "Referência já vinculada a pagamento. Use o histórico do pagamento, sem nova baixa documental")
    _cas(db, n)
    if n.cancelada:
        db.rollback()
        raise HTTPException(422, "Nota cancelada")
    if body.data > hoje():
        db.rollback()
        raise HTTPException(422, "Abatimento documental não pode ter data futura")
    if body.data < n.data_emissao:
        db.rollback()
        raise HTTPException(422, "Abatimento não pode anteceder a emissão")
    saldo = round(n.valor_original - _total(db, nid), 2)
    if body.valor > Decimal(str(saldo)):
        db.rollback()
        raise HTTPException(422, "Valor excede o saldo da nota")
    a = NotaAbatimento(nota_id=nid, valor=float(body.valor), data=body.data,
        referencia=body.referencia, referencia_chave=chave_referencia(body.referencia), observacao=body.observacao,
        chave_idempotencia=body.chave_idempotencia, created_by=u.id)
    db.add(a)
    db.flush()
    audit(db, u.id, "nota_abatimento_registrado", "nota_abatimentos", a.id, depois=body.model_dump())
    db.commit()
    return _abatimento_out(db, a)


@r.post("/notas/{nid}/abatimentos/{aid}/estornar")
def estornar(nid: int, aid: int, body: DesfazerIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    confere_senha(u, body.senha)
    n = _nota(db, nid)
    a = db.query(NotaAbatimento).filter_by(id=aid, nota_id=nid).first()
    if not a:
        raise HTTPException(404, "Abatimento não encontrado")
    if a.pagamento_aplicacao_id is not None or a.credito_aplicacao_id is not None:
        raise HTTPException(422, "Estorne pelo pagamento para preservar os dois históricos")
    _cas(db, n)
    if a.estornado or n.cancelada:
        db.rollback()
        raise HTTPException(422, "Abatimento já estornado ou nota cancelada")
    a.estornado = True
    db.add(NotaAbatimentoEstorno(abatimento_id=a.id, motivo=body.motivo, created_by=u.id))
    audit(db, u.id, "nota_abatimento_estornado", "nota_abatimentos", a.id, depois={"motivo": body.motivo})
    db.commit()
    return _abatimento_out(db, a)


@r.post("/notas/{nid}/cancelar")
def cancelar(nid: int, body: DesfazerIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    confere_senha(u, body.senha)
    n = _nota(db, nid)
    _cas(db, n)
    if n.cancelada or _total(db, nid) > 0:
        db.rollback()
        raise HTTPException(422, "Nota cancelada ou com abatimentos ativos: estorne antes")
    n.cancelada = True
    n.motivo_cancelamento = body.motivo
    audit(db, u.id, "nota_cancelada", "notas_obrigacoes", nid, depois={"motivo": body.motivo})
    db.commit()
    return _out(db, n)


def _anexo(db, nid, aid):
    _nota(db, nid)
    a = db.query(NotaAnexo).filter_by(id=aid, nota_id=nid, ativo=True).first()
    if not a:
        raise HTTPException(404, "Anexo não encontrado")
    return a


@r.post("/notas/{nid}/anexos", status_code=201)
async def anexar(nid: int, f: UploadFile = File(...), db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    n = _nota(db, nid)
    if n.cancelada:
        raise HTTPException(422, "Nota cancelada")
    data = await f.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    await f.close()
    if not data or len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(422, "Arquivo vazio ou maior que o limite permitido")
    nome = re.sub(r"[\x00-\x1f\x7f]", "", (f.filename or "anexo").replace("\\", "/").split("/")[-1])[:180]
    ext = Path(nome).suffix.lower()
    formato = ".pdf" if data.startswith(b"%PDF-") else ".png" if data.startswith(b"\x89PNG\r\n\x1a\n") else ".jpg" if data.startswith(b"\xff\xd8\xff") else ".webp" if data[:4] == b"RIFF" and data[8:12] == b"WEBP" else None
    if not formato or ext not in ((".jpg", ".jpeg") if formato == ".jpg" else (formato,)):
        raise HTTPException(422, "Formato deve ser PDF, PNG, JPEG ou WebP válido e compatível com a extensão")
    _cas(db, n)
    path = upload_root(db, base=UPLOAD_DIR) / "notas" / str(nid) / (uuid4().hex + formato)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.resolve() != path.parent:
        raise HTTPException(503, "Diretório de anexos indisponível")
    try:
        path.write_bytes(data)
        a = NotaAnexo(nota_id=nid, nome_original=nome, arquivo_path=str(path), tamanho=len(data), created_by=u.id)
        db.add(a)
        db.flush()
        audit(db, u.id, "nota_anexo_adicionado", "nota_anexos", a.id, depois={"nome": nome, "tamanho": len(data)})
        db.commit()
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise
    return _anexo_out(a)


@r.get("/notas/{nid}/anexos/{aid}/arquivo")
def baixar(nid: int, aid: int, db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    a = _anexo(db, nid, aid)
    path = Path(a.arquivo_path).resolve()
    root = upload_root(db, base=UPLOAD_DIR) / "notas" / str(nid)
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(404, "Arquivo indisponível")
    return FileResponse(path, media_type="application/octet-stream", filename=a.nome_original,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


@r.delete("/notas/{nid}/anexos/{aid}")
def desativar(nid: int, aid: int, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    a = _anexo(db, nid, aid)
    a.ativo = False
    audit(db, u.id, "nota_anexo_desativado", "nota_anexos", aid)
    db.commit()
    return {"id": aid, "ativo": False}
