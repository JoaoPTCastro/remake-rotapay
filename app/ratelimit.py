"""Sprint D1: rate limiting simples em memória (login + upload).

Sem dependência externa: janela fixa por IP. Estoura -> 429.
Suficiente p/ MVP; trocar por Redis quando houver vài instâncias.
"""
from .proxy_identity import client_ip
import time
from collections import defaultdict, deque
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# (prefixo, métodos|None=todos): (requisições, janela_segundos)
LIMITES = {
    "/organizacoes/convites/registrar": ("POST", 10, 60),
    "/organizacoes/convites/aceitar": ("POST", 20, 60),
    "/publico/extratos": (None, 60, 60),
    "/auth/login": (None, 10, 60),
    "/auth/me/password": (None, 5, 60),           # troca de senha (força bruta da atual)
    "/movimentacoes/": ("POST", 30, 60),       # uploads de comprovante
    "/conciliacoes": (None, 60, 60),           # rotas de dinheiro
    "/webhooks/checkto": (None, 120, 60),
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        for prefix, (metodos, limite, janela) in LIMITES.items():
            if metodos and request.method not in (metodos if isinstance(metodos, tuple) else (metodos,)):
                continue
            casa = (
                path == prefix
                or path.startswith(prefix.rstrip("/") + "/")
                or (
                    prefix == "/movimentacoes/"
                    and request.method == "POST"
                    and "/comprovante" in path
                )
            )
            if not casa:
                continue
            ip = client_ip(request)
            chave = f"{prefix}:{ip}"
            agora = time.time()
            fila = self.hits[chave]
            while fila and fila[0] <= agora - janela:
                fila.popleft()
            if len(fila) >= limite:
                return JSONResponse({"detail": "Muitas tentativas. Aguarde um minuto."},
                                    status_code=429)
            fila.append(agora)
        return await call_next(request)
