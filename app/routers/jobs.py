"""Sprint B2/C: fila + worker da simulação de OCR experimental."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Job, Comprovante, Movimentacao, Pessoa, User
from ..auth import need
from ..audit import audit
from ..ocr import extrair, sugerir_fornecedor, dumps

r = APIRouter(prefix="/jobs", tags=["jobs"])


@r.get("")
def listar(status: str | None = None, db: Session = Depends(get_db),
           u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    q = db.query(Job).order_by(Job.id.desc())
    if status:
        q = q.filter(Job.status == status)
    return [{"id": j.id, "tipo": j.tipo, "ref_id": j.ref_id,
             "status": j.status, "detalhe": j.detalhe} for j in q.limit(200).all()]


@r.post("/processar")
def processar(db: Session = Depends(get_db),
              u: User = Depends(need("admin", "financeiro"))):
    """Processa jobs aptos e mantém sem vínculo em espera reativável."""
    pend = db.query(Job).filter_by(status="pendente").all()
    processados = 0
    aguardando_vinculo = 0
    ignorados = 0
    erros = 0
    for j in pend:
        if j.tipo == "comprovante":
            c = db.get(Comprovante, j.ref_id)
            if not c:
                j.status = "erro"
                j.detalhe = "comprovante não encontrado"
                erros += 1
                continue
            if c.etapa == "rejeitado":
                j.status = "ignorado"
                j.detalhe = "comprovante rejeitado; OCR não executado"
                ignorados += 1
                continue
            if not c.movimentacao_id:
                j.status = "aguardando_vinculo"
                j.detalhe = "aguardando vínculo com movimentação; OCR experimental não executado"
                aguardando_vinculo += 1
                continue
            m = db.get(Movimentacao, c.movimentacao_id)
            if not m:
                j.status = "erro"
                j.detalhe = "movimentação vinculada não encontrada"
                erros += 1
                continue
            ext = extrair(m.valor, str(m.data_pix), m.remetente, m.destinatario)
            c.extraido_json = dumps(ext)
            conf = min(v["confianca"] for v in ext.values())
            forns = [(p.id, p.nome) for p in db.query(Pessoa).filter_by(
                ativo=True).filter(Pessoa.tipo.in_(["fornecedor", "ambos"])).all()]
            fid, motivo = sugerir_fornecedor(m.remetente, forns)
            if fid:
                c.sugestao_fornecedor_id = fid
                c.sugestao_motivo = motivo
                c.sugestao_status = "pendente"
            j.status = "processado"
            j.detalhe = ("OCR experimental (simulado): extração + sugestão "
                         f"(revisão humana) | confiança mín {conf:.0%}")
            processados += 1
        else:
            j.status = "processado"
            processados += 1
    audit(db, u.id, "jobs_processados", "jobs", None, depois={
        "processados": processados,
        "aguardando_vinculo": aguardando_vinculo,
        "ignorados": ignorados,
        "erros": erros,
    })
    for j in pend:
        if j.tipo == "comprovante":
            acao = {
                "processado": "comprovante_processado",
                "aguardando_vinculo": "comprovante_aguardando_vinculo",
                "ignorado": "comprovante_ignorado",
                "erro": "comprovante_processamento_erro",
            }[j.status]
            audit(db, u.id, acao, "comprovantes", j.ref_id,
                  depois={"status": j.status})
    db.commit()
    return {"processados": processados,
            "aguardando_vinculo": aguardando_vinculo,
            "ignorados": ignorados,
            "erros": erros}
