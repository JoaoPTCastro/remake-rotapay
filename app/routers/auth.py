from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
import os
from ..database import get_control_db as get_db
from ..models import User
from ..auth import hash_pw, check_pw, token_for, current_user, need
from ..schemas import LoginIn, SenhaIn, UserCreateIn, UserOut, UserPasswordResetIn, UserUpdateIn, PerfilUpdateIn
from ..audit import audit

r = APIRouter(prefix="/auth", tags=["auth"])


@r.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == body.email).first()
    if not u or not check_pw(body.senha, u.senha_hash):
        raise HTTPException(401, "Credenciais inválidas")
    if not u.ativo:
        raise HTTPException(403, "Usuário inativo")
    audit(db, u.id, "login", "users", u.id)
    db.commit()
    from ..organizacoes_models import Organizacao, VinculoOrganizacao
    membro = db.query(VinculoOrganizacao).join(Organizacao).filter(
        VinculoOrganizacao.user_id == u.id, VinculoOrganizacao.ativo.is_(True),
        Organizacao.ativo.is_(True),
    ).order_by(VinculoOrganizacao.organizacao_id).first()
    org_id = membro.organizacao_id if membro else 1
    papel = membro.perfil if membro else u.perfil
    return {"access_token": token_for(u, org_id), "token_type": "bearer",
            "user": {"id": u.id, "nome": u.nome, "email": u.email, "perfil": papel}}


@r.post("/seed-admin")
def seed_admin(body: dict | None = None, db: Session = Depends(get_db)):
    """Cria admin inicial se não existir.

    Em produção exige SETUP_TOKEN (senha descartável definida no ambiente):
    sem ele, 403 — ninguém sequestra a instância fresca.
    """
    if db.query(User).first():
        raise HTTPException(409, "Já existem usuários")
    if os.getenv("ENV", "dev") == "prod":
        esperado = os.getenv("SETUP_TOKEN", "")
        if not esperado or (body or {}).get("setup_token") != esperado:
            raise HTTPException(403, "Setup desabilitado: informe setup_token válido")
    u = User(nome="Admin", email="admin@local", senha_hash=hash_pw("admin123"), perfil="admin")
    db.add(u)
    db.flush()
    from ..organizacoes_bootstrap import vincular_usuario_original
    vincular_usuario_original(db, u)
    audit(db, None, "seed_admin", "users", u.id)
    db.commit()
    return {"email": "admin@local", "senha": "admin123"}


@r.get("/me")
def me(request: Request, u: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..organizacoes_models import Organizacao, VinculoOrganizacao
    org_id = getattr(request.state, "organizacao_id", 1)
    org = db.get(Organizacao, org_id)
    vinculo = db.query(VinculoOrganizacao).filter_by(user_id=u.id, organizacao_id=org_id, ativo=True).first()
    papel = vinculo.perfil if org and org.ativo and vinculo else u.perfil
    resposta = {"id": u.id, "nome": u.nome, "email": u.email, "perfil": papel}
    if org:
        resposta.update(organizacao_id=org_id, organizacao_nome=org.nome if vinculo else None)
    return resposta


def _user_snapshot(user):
    return {"nome": user.nome, "email": user.email, "perfil": user.perfil, "ativo": user.ativo}


def _email_disponivel(db, email, user_id):
    if db.query(User).filter(func.lower(User.email) == email, User.id != user_id).first():
        raise HTTPException(409, "Email já cadastrado")


@r.patch("/me", response_model=UserOut)
def editar_me(body: PerfilUpdateIn, db: Session = Depends(get_db), u: User = Depends(current_user)):
    if body.email is not None and body.email != u.email:
        if not body.senha_atual or not check_pw(body.senha_atual, u.senha_hash):
            raise HTTPException(403, "Confirme a senha atual para alterar o email")
        _email_disponivel(db, body.email, u.id)
    before = _user_snapshot(u)
    for field in ("nome", "email"):
        value = getattr(body, field)
        if value is not None:
            setattr(u, field, value)
    audit(db, u.id, "perfil_atualizado", "users", u.id, antes=before, depois=_user_snapshot(u))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email já cadastrado")
    db.refresh(u)
    return u


@r.get("/permissoes")
def permissoes(request: Request, u: User = Depends(current_user), db: Session = Depends(get_db)):
    from fastapi.routing import APIRoute
    from ..auth import PERFIS

    def restricoes(dep):
        groups = []
        roles = getattr(dep.call, "perfis", None)
        if roles is not None:
            groups.append(set(roles))
        elif dep.call is current_user:
            groups.append(set(PERFIS))
        for child in dep.dependencies:
            groups.extend(restricoes(child))
        return groups

    def api_routes():
        for item in request.app.routes:
            if isinstance(item, APIRoute):
                yield item
            elif hasattr(item, "effective_route_contexts"):
                # FastAPI 0.141 mantém routers incluídos como contextos efetivos.
                for context in item.effective_route_contexts():
                    if isinstance(context.original_route, APIRoute):
                        yield context

    from ..organizacoes_models import Organizacao, VinculoOrganizacao
    # Papel do ambiente selecionado; nunca altera o perfil da identidade central.
    org_id = getattr(request.state, "organizacao_id", 1)
    vinculo = db.query(VinculoOrganizacao).join(Organizacao).filter(
        VinculoOrganizacao.user_id == u.id, VinculoOrganizacao.organizacao_id == org_id,
        VinculoOrganizacao.ativo.is_(True), Organizacao.ativo.is_(True)).first()
    papel = vinculo.perfil if vinculo else (u.perfil if org_id == 1 else "sem_acesso")
    u = User(id=u.id, nome=u.nome, email=u.email, perfil=papel)
    actions = []
    for route in api_routes():
        groups = restricoes(route.dependant)
        if not groups:
            continue
        allowed = set(PERFIS).intersection(*groups)
        if org_id != 1 and route.path.startswith("/auth/users"):
            allowed = set()
        for method in sorted(route.methods):
            actions.append({"metodo": method, "rota": route.path, "grupo": route.tags[0] if route.tags else "geral",
                            "perfis": [role for role in PERFIS if role in allowed], "permitido": u.perfil in allowed})
    if u.perfil != "admin":
        actions = [{**item, "perfis": [u.perfil]} for item in actions if item["permitido"]]
    actions.sort(key=lambda item: (item["grupo"], item["rota"], item["metodo"]))
    return {"perfil": u.perfil, "acoes": actions,
            "matriz": [{"perfil": role, "acoes": [f'{a["metodo"]} {a["rota"]}' for a in actions if role in a["perfis"]]} for role in PERFIS] if u.perfil == "admin" else None}


@r.post("/me/password")
def minha_senha(body: SenhaIn, db: Session = Depends(get_db),
                u: User = Depends(current_user)):
    """Troca a própria senha. Sessões antigas expiram (hash muda -> pwh muda)."""
    if not check_pw(body.senha_atual, u.senha_hash):
        raise HTTPException(403, "Senha atual incorreta")
    u.senha_hash = hash_pw(body.nova)
    audit(db, u.id, "senha_alterada", "users", u.id)
    db.commit()
    return {"ok": True}


def _bloquear_administracao(db: Session, admin: User):
    """Serializa alterações de acesso no banco até commit/rollback.

    SQLite adquire o lock de escrita sem disparar onupdate do ORM. PostgreSQL
    serializa escritores de users. A contagem e o papel do ator são relidos
    após o lock, portanto duas transações não removem os últimos dois admins.
    """
    dialect = db.get_bind().dialect.name
    try:
        if dialect == "sqlite":
            db.execute(text("UPDATE users SET ativo = ativo WHERE perfil = 'admin'"))
        elif dialect == "postgresql":
            db.execute(text("LOCK TABLE users IN SHARE ROW EXCLUSIVE MODE"))
        else:
            raise HTTPException(503, "Banco não suportado para administração concorrente")
    except OperationalError:
        db.rollback()
        raise HTTPException(409, "Administração em atualização. Recarregue e tente novamente")
    db.expire_all()
    db.refresh(admin)
    if not admin.ativo or admin.perfil != "admin":
        db.rollback()
        raise HTTPException(403, "Sem permissão")


def _usuarios_instancia(db):
    from ..organizacoes_models import Organizacao, VinculoOrganizacao, FornecedorIdentidade
    query = db.query(User)
    if db.query(Organizacao.id).first() is not None:
        query = query.join(VinculoOrganizacao, VinculoOrganizacao.user_id == User.id).filter(
            VinculoOrganizacao.organizacao_id == 1,
            VinculoOrganizacao.perfil.in_(("admin", "financeiro", "operador", "consulta")),
            ~db.query(FornecedorIdentidade.id).filter(FornecedorIdentidade.user_id == User.id).exists())
    return query


@r.get("/users", response_model=list[UserOut])
def list_users(_: User = Depends(need("admin")), db: Session = Depends(get_db)):
    return _usuarios_instancia(db).order_by(User.id).all()


@r.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreateIn, admin: User = Depends(need("admin")),
                db: Session = Depends(get_db)):
    _bloquear_administracao(db, admin)
    exists = db.query(User).filter(func.lower(User.email) == body.email).first()
    if exists:
        raise HTTPException(409, "Email já cadastrado")

    user = User(
        nome=body.nome,
        email=body.email,
        senha_hash=hash_pw(body.senha),
        perfil=body.perfil,
        ativo=body.ativo,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email já cadastrado")
    from ..organizacoes_bootstrap import vincular_usuario_original
    vincular_usuario_original(db, user)
    audit(db, admin.id, "usuario_criado", "users", user.id, depois={
        "nome": user.nome,
        "email": user.email,
        "perfil": user.perfil,
        "ativo": user.ativo,
    })
    db.commit()
    db.refresh(user)
    return user


def _identidade_restrita_a_original(db, user):
    from ..organizacoes_models import VinculoOrganizacao
    if db.query(VinculoOrganizacao.id).filter(
            VinculoOrganizacao.user_id == user.id,
            VinculoOrganizacao.organizacao_id != 1).first():
        raise HTTPException(403, "Identidade compartilhada: use o perfil pessoal ou gestão do vínculo")


@r.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdateIn,
                admin: User = Depends(need("admin")), db: Session = Depends(get_db)):
    _bloquear_administracao(db, admin)
    user = _usuarios_instancia(db).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    _identidade_restrita_a_original(db, user)
    if user.id == admin.id and body.email is not None and body.email != user.email:
        raise HTTPException(422, "Altere seu email em Meu perfil, confirmando a senha atual")
    if user.id == admin.id and body.ativo is False:
        raise HTTPException(422, "Não é possível desativar a própria conta")

    removes_active_admin = (
        user.ativo
        and user.perfil == "admin"
        and (body.ativo is False or (body.perfil is not None and body.perfil != "admin"))
    )
    if removes_active_admin:
        active_admins = _usuarios_instancia(db).filter(
            User.perfil == "admin", User.ativo.is_(True)
        ).count()
        if active_admins <= 1:
            raise HTTPException(422, "Não é possível remover o último admin ativo")

    before = _user_snapshot(user)
    if body.email is not None:
        _email_disponivel(db, body.email, user.id)
    for field in ("nome", "email"):
        value = getattr(body, field)
        if value is not None:
            setattr(user, field, value)
    if body.perfil is not None:
        user.perfil = body.perfil
    if body.ativo is not None:
        user.ativo = body.ativo
    from ..organizacoes_bootstrap import atualizar_vinculo_original
    atualizar_vinculo_original(db, user)
    after = _user_snapshot(user)
    if body.motivo:
        after["motivo"] = body.motivo
    audit(db, admin.id, "usuario_atualizado", "users", user.id,
          antes=before, depois=after)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email já cadastrado")
    db.refresh(user)
    return user


@r.post("/users/{user_id}/password")
def reset_user_password(user_id: int, body: UserPasswordResetIn,
                        admin: User = Depends(need("admin")), db: Session = Depends(get_db)):
    _bloquear_administracao(db, admin)
    user = _usuarios_instancia(db).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    if user.id == admin.id:
        raise HTTPException(422, "Altere sua senha em Meu perfil, confirmando a senha atual")
    _identidade_restrita_a_original(db, user)
    user.senha_hash = hash_pw(body.senha)
    audit(db, admin.id, "usuario_senha_redefinida", "users", user.id)
    db.commit()
    return {"ok": True}
