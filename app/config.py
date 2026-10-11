"""Config + engine SQLAlchemy migrável SQLite -> Postgres.

Use DATABASE_URL env. Padrão: sqlite local.
Ex. Postgres futuro: postgresql+psycopg://user:pass@host/db
"""
import os

_DEV_SECRET = "dev-secret-trocar-em-producao"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pix.db")
SECRET_KEY = os.getenv("SECRET_KEY", _DEV_SECRET)
if os.getenv("ENV", "dev") == "prod" and SECRET_KEY == _DEV_SECRET:
    raise RuntimeError("ENV=prod exige SECRET_KEY própria (fail-closed)")
ALGORITHM = "HS256"
TOKEN_MINUTES = int(os.getenv("TOKEN_MINUTES", "480"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
ALLOWED_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
# Sprint gateway (Checkto llms.txt)
CHECKTO_PUBLIC_KEY = os.getenv("CHECKTO_PUBLIC_KEY", "")
CHECKTO_SECRET_KEY = os.getenv("CHECKTO_SECRET_KEY", "")
CHECKTO_CALLBACK_URL = os.getenv("CHECKTO_CALLBACK_URL", "")  # URL fixa e pública
CHECKTO_WEBHOOK_TOKEN = os.getenv("CHECKTO_WEBHOOK_TOKEN", "")  # token do painel (fallback)
