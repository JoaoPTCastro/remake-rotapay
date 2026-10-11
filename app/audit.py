import json
from contextvars import ContextVar, Token
from sqlalchemy.orm import Session
from .models import AuditLog

ANALYTICS = {"login", "movimentacao_criada", "movimentacao_editada",
             "movimentacao_excluida", "projecao_criada", "projecao_atualizada",
             "conciliacao_criada", "conciliacao_estornada", "comprovante_anexado",
             "relatorio_exportado", "lancamento_criado", "lancamento_cancelado",
             "sugestao_decidida", "pagamento_checkto", "link_criado",
             "link_revogado", "cobranca_criada", "seed_admin"}


_ip_atual: ContextVar[str] = ContextVar("audit_ip", default="")


def fixar_ip(ip: str | None) -> Token:
    """Guarda o IP do request p/ o audit() usar. Devolve token p/ reset."""
    return _ip_atual.set(ip or "")


def soltar_ip(token: Token) -> None:
    _ip_atual.reset(token)


def audit(db: Session, usuario_id: int | None, acao: str, entidade: str,
          entidade_id: int | None = None, antes=None, depois=None,
          ip: str | None = None):
    from .organizacoes_audit import AuditOrganizacao, identidade_compartilhada
    # Logs centrais não pertencem ao extrato/auditoria privada da loja original.
    central = entidade == "organizacao" or (
        entidade == "users" and (
            identidade_compartilhada(db, usuario_id) or identidade_compartilhada(db, entidade_id)))
    modelo = AuditOrganizacao if central else AuditLog
    db.add(modelo(
        usuario_id=usuario_id,
        acao=acao,
        entidade=entidade,
        entidade_id=entidade_id,
        antes=json.dumps(antes, default=str)[:4000] if antes is not None else "",
        depois=json.dumps(depois, default=str)[:4000] if depois is not None else "",
        ip=ip if ip is not None else _ip_atual.get(),
    ))
