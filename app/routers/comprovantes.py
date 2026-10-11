"""Leitura autenticada de comprovantes preservados na operação."""
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..ambientes import upload_root
from ..models import Comprovante, User
from ..auth import need
from ..config import UPLOAD_DIR

r = APIRouter(tags=["comprovantes"])

@r.get("/comprovantes/{cid}/arquivo")
def arquivo(cid: int, db: Session = Depends(get_db),
            u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    """Ver o comprovante (imagem/PDF) direto no navegador."""
    c = db.get(Comprovante, cid)
    if not c or not c.arquivo_path or not os.path.exists(c.arquivo_path):
        raise HTTPException(404, "Arquivo não encontrado")
    path = Path(c.arquivo_path).resolve()
    root = upload_root(db, base=UPLOAD_DIR)
    if (not path.is_relative_to(root)
            or (db.info.get("organizacao_id", 1) == 1 and path.is_relative_to(root / "organizacoes"))):
        raise HTTPException(404, "Arquivo não encontrado")
    return FileResponse(path, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
