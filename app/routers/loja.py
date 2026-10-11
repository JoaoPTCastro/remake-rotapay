"""Dados da empresa e logo raster privado, independentes da marca RotaPay."""
from io import BytesIO
from pathlib import Path
import uuid
import os
from tempfile import NamedTemporaryFile
import warnings
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from PIL import Image, UnidentifiedImageError
from ..database import get_db
from ..ambientes import upload_root
from ..models import Loja, User
from ..auth import need
from ..audit import audit
from ..schemas import LojaIn
from ..config import UPLOAD_DIR

r = APIRouter(prefix="/loja", tags=["loja"])
LEITURA = need("admin", "financeiro", "operador", "consulta")
ESCRITA = need("admin", "financeiro")
MAX_LOGO_BYTES = 2 * 1024 * 1024
MAX_LOGO_DIM = 2048
MAX_LOGO_PIXELS = 4_000_000


def _get(db, criar=False):
    loja = db.query(Loja).order_by(Loja.id).first()
    if not loja and criar:
        loja = Loja(nome="Minha Loja")
        db.add(loja)
        db.flush()
    return loja


def _out(l):
    if l is None:
        return {"id": None, "nome": "Minha Loja", "documento": "", "telefone": "", "email": "", "endereco": "", "tem_logo": False, "logo_url": None}
    return {"id": l.id, "nome": l.nome, "documento": l.documento,
            "telefone": l.telefone, "email": l.email, "endereco": l.endereco,
            "tem_logo": bool(l.logo_arquivo), "logo_url": "/loja/logo" if l.logo_arquivo else None}


@r.get("")
def ler(db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    return _out(_get(db))


@r.patch("")
def editar(body: LojaIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    loja = _get(db, criar=True)
    before = _out(loja)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(loja, k, v)
    audit(db, u.id, "loja_atualizada", "loja", loja.id, antes=before, depois=_out(loja))
    db.commit()
    return _out(loja)


def _logo_root(db):
    uploads = upload_root(db, base=UPLOAD_DIR)
    root = (uploads / "loja-logos").resolve()
    if root.parent != uploads:
        raise HTTPException(404, "Diretório de logo indisponível")
    return root


@r.post("/logo")
async def enviar_logo(arquivo: UploadFile = File(...), db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    try:
        data = await arquivo.read(MAX_LOGO_BYTES + 1)
    finally:
        await arquivo.close()
    if not data or len(data) > MAX_LOGO_BYTES:
        raise HTTPException(422, "Logo deve conter até 2 MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data), formats=("PNG", "JPEG", "WEBP")) as image:
                width, height = image.size
                if width > MAX_LOGO_DIM or height > MAX_LOGO_DIM or width * height > MAX_LOGO_PIXELS:
                    raise ValueError("dimensões")
                if getattr(image, "n_frames", 1) != 1:
                    raise ValueError("imagem animada")
                image.load()
                clean = Image.new("RGBA", image.size)
                clean.paste(image.convert("RGBA"))
                output = BytesIO()
                clean.save(output, format="PNG")
                encoded = output.getvalue()
                if len(encoded) > MAX_LOGO_BYTES:
                    raise ValueError("PNG resultante excede limite")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(422, "Use PNG, JPEG ou WebP estático válido, até 2048 px por lado e 4 milhões de pixels")
    root = _logo_root(db)
    root.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    path = root / filename
    with NamedTemporaryFile(dir=root, suffix=".tmp", delete=False) as temporary:
        temporary.write(encoded)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    try:
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)
    try:
        loja = _get(db, criar=True)
        before = {"tem_logo": bool(loja.logo_arquivo)}
        loja.logo_arquivo = filename
        audit(db, u.id, "loja_logo_atualizado", "loja", loja.id, antes=before, depois={"tem_logo": True})
        db.commit()
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise
    return _out(loja)


@r.get("/logo")
def baixar_logo(db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    loja = _get(db)
    if not loja or not loja.logo_arquivo:
        raise HTTPException(404, "Logo não cadastrado")
    root = _logo_root(db)
    path = (root / loja.logo_arquivo).resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(404, "Logo não encontrado")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "default-src 'none'; sandbox"})


@r.delete("/logo")
def remover_logo(db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    loja = _get(db)
    if loja:
        before = {"tem_logo": bool(loja.logo_arquivo)}
        loja.logo_arquivo = None
        audit(db, u.id, "loja_logo_removido", "loja", loja.id, antes=before, depois={"tem_logo": False})
        db.commit()
    return _out(loja)
