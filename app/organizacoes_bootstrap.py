"""Transição aditiva da instância original; nunca provisiona acesso por login."""
from .models import Loja, User
from .organizacoes_models import Organizacao, VinculoOrganizacao


def inicializar_organizacao_original(db):
    # Snapshot único. Reiniciar não reativa vínculos revogados nem incorpora fornecedores.
    if db.query(Organizacao.id).first() is not None:
        return
    loja = db.query(Loja).order_by(Loja.id).first()
    db.add(Organizacao(id=1, nome=loja.nome if loja else "Minha Loja", ativo=True))
    db.flush()
    for user in db.query(User).filter(User.perfil.in_(("admin", "financeiro", "operador", "consulta"))).all():
        vincular_usuario_original(db, user)
    db.commit()


def vincular_usuario_original(db, user):
    if not db.get(Organizacao, 1):
        return  # Compatibilidade com banco antigo ainda não inicializado.
    if not db.query(VinculoOrganizacao).filter_by(user_id=user.id, organizacao_id=1).first():
        db.add(VinculoOrganizacao(user_id=user.id, organizacao_id=1, perfil=user.perfil, ativo=user.ativo))


def atualizar_vinculo_original(db, user):
    vinculo = db.query(VinculoOrganizacao).filter_by(user_id=user.id, organizacao_id=1).first()
    if vinculo:
        vinculo.perfil = user.perfil
        vinculo.ativo = user.ativo
