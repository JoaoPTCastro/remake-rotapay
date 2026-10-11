"""Aliases públicos resolvem a loja pelo caminho, sem procurar tokens entre bancos."""
import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class PublicAmbienteMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.scope["path"]
        if path.startswith("/lojas/"):
            match = re.fullmatch(r"/lojas/([1-9][0-9]{0,8})(/links/v/[A-Za-z0-9_-]{1,128}|/publico/extratos)", path)
            if not match:
                return JSONResponse({"detail": "Acesso indisponível"}, status_code=404)
            request.state.public_organizacao_id = int(match[1])
            request.scope["path"] = match[2]
            request.scope["raw_path"] = match[2].encode()
        response = await call_next(request)
        if path.startswith(("/lojas/", "/links/v/", "/publico/", "/convite")):
            response.headers.update({"Cache-Control": "private, no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff"})
        return response
