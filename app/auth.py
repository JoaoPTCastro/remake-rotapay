import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .config import SECRET_KEY, ALGORITHM, TOKEN_MINUTES
from .database import get_db, get_control_db
from .models import User

bearer = HTTPBearer(auto_error=False)
PERFIS = ("admin", "financeiro", "operador", "consulta")
DEV_BYPASS_AUTH = os.getenv("DEV_BYPASS_AUTH", "false").lower() == "true"
DEV_BYPASS_EMAIL = os.getenv("DEV_BYPASS_EMAIL", "admin@local")


def hash_pw(p: str) -> str:
    salt = os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", p.encode(), bytes.fromhex(salt), 200_000).hex()
    return f"pbkdf2${salt}${h}"


def check_pw(p: str, h: str) -> bool:
    try:
        _, salt, digest = h.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", p.encode(), bytes.fromhex(salt), 200_000).hex()
        return hmac.compare_digest(calc, digest)
    except Exception:
        return False


def _pwh(u: User) -> str:
    """Fingerprint derivado do hash inteiro: muda sempre que a senha muda."""
    return hashlib.sha256(u.senha_hash.encode()).hexdigest()[:12]


def token_for(user: User, organizacao_id: int = 1) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES)
    return jwt.encode({"sub": str(user.id), "perfil": user.perfil,
                       "pwh": _pwh(user), "org": organizacao_id, "exp": exp},
                      SECRET_KEY, ALGORITHM)


def autenticar_token(token: str, db: Session):
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uid = int(data["sub"])
        org = data.get("org", 1)
        if not isinstance(org, int) or isinstance(org, bool) or org < 1:
            raise ValueError()
    except (JWTError, KeyError, ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")
    u = db.get(User, uid)
    if not u or not u.ativo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário inativo")
    if data.get("pwh") != _pwh(u):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão expirada: entre novamente")
    return u, org


def _dev_bypass_user(db: Session) -> User:
    u = db.query(User).filter(User.email == DEV_BYPASS_EMAIL).first()
    if u:
        return u
    u = User(nome="Admin dev", email=DEV_BYPASS_EMAIL, senha_hash=hash_pw("admin123"), perfil="admin", ativo=True)
    db.add(u)
    db.flush()
    try:
        from .organizacoes_bootstrap import vincular_usuario_original
        vincular_usuario_original(db, u)
    except Exception:
        pass
    db.commit()
    db.refresh(u)
    return u


def current_user(request: Request, creds: HTTPAuthorizationCredentials | None = Depends(bearer),
                 db: Session = Depends(get_control_db)) -> User:
    if creds is None:
        if DEV_BYPASS_AUTH:
            request.state.organizacao_id = 1
            return _dev_bypass_user(db)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Não autenticado")
    user, org_id = autenticar_token(creds.credentials, db)
    request.state.organizacao_id = org_id
    return user


def confere_senha(u: User, senha: str | None):
    """Exige a senha do próprio usuário p/ desfazer dinheiro (anti-clique-sem-querer)."""
    if not senha or not check_pw(senha, u.senha_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Confirme com a sua senha para concluir")


def acesso_financeiro(db: Session, u: User, request: Request, perfis: tuple[str, ...]):
    from .organizacoes_models import Organizacao, VinculoOrganizacao
    from sqlalchemy import select
    org_id = getattr(request.state, "organizacao_id", db.info.get("organizacao_id", 1))
    contexto = request.headers.get("X-Organizacao-Id")
    if contexto is not None and contexto != str(org_id):
        raise HTTPException(403, "Contexto de organização incompatível")
    if request.url.path.startswith("/auth/users") and org_id != 1:
        raise HTTPException(403, "Administração de identidades disponível na operação original")
    central = db.info.get("controle_session", db)
    membro_perfil = select(VinculoOrganizacao.perfil).join(Organizacao).where(
        VinculoOrganizacao.user_id == u.id,
        VinculoOrganizacao.organizacao_id == org_id,
        VinculoOrganizacao.ativo.is_(True), Organizacao.ativo.is_(True),
    ).scalar_subquery()
    registrado, papel = central.execute(select(select(Organizacao.id).exists(), membro_perfil)).one()
    if registrado and papel not in perfis:
        raise HTTPException(403, "Sem acesso financeiro neste ambiente")
    if org_id == 1 and u.perfil not in perfis:
        raise HTTPException(403, "Sem permissão")
    return papel or u.perfil


def need(*perfis: str):
    def dep(request: Request, u: User = Depends(current_user), db: Session = Depends(get_db)) -> User:
        papel = acesso_financeiro(db, u, request, perfis)
        if db.info.get("organizacao_id", 1) != 1 and not request.url.path.startswith("/auth/"):
            # Projeção do ator para regras/assinaturas locais, sem mutar identidade central.
            return User(id=u.id, nome=u.nome, email=u.email, senha_hash=u.senha_hash,
                        perfil=papel, ativo=u.ativo)
        return u
    dep.perfis = tuple(perfis)
    return dep
