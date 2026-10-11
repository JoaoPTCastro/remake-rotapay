"""Visualização autenticada dos mesmos arquivos privados já aceitos no upload."""
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse


def tipo_mime(path):
    try:
        with Path(path).open("rb") as file:
            signature = file.read(16)
    except OSError:
        return None
    if signature.startswith(b"%PDF-"): return "application/pdf"
    if signature.startswith(b"\x89PNG\r\n\x1a\n"): return "image/png"
    if signature.startswith(b"\xff\xd8\xff"): return "image/jpeg"
    if signature[:4] == b"RIFF" and signature[8:12] == b"WEBP": return "image/webp"
    return None


def mime_privado(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    return tipo_mime(path) if path.is_relative_to(root) and path.is_file() else None


def resposta_arquivo(path, nome, inline=False):
    headers = {"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"}
    mime = "application/octet-stream"
    if inline:
        mime = tipo_mime(path)
        if not mime:
            raise HTTPException(415, "Visualização indisponível para este formato; baixe o original")
        # PDF pode conter conteúdo ativo; o navegador recebe um documento isolado.
        headers["Content-Security-Policy"] = "sandbox; default-src 'none'; frame-ancestors 'self'"
    return FileResponse(path, media_type=mime, filename=nome, content_disposition_type="inline" if inline else "attachment", headers=headers)
