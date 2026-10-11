from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from .database import init_db
from . import organizacoes_audit  # registra modelos de auditoria central
from .audit import fixar_ip, soltar_ip
from .routers import auth, pessoas, movimentacoes, financeiro, dashboard, export, links, jobs, webhooks, comprovantes, loja, notas, pagamentos, acertos, creditos, extratos, intercambio, cadastros_consulta, configuracoes, compartilhamentos_extratos, legado, visao_geral, organizacoes
from .routers import cadastro_publico, interesse_lojas
from .ratelimit import RateLimitMiddleware
from .middleware_ambientes import PublicAmbienteMiddleware


logging.basicConfig(level=logging.INFO,
                    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}')


class IPMiddleware(BaseHTTPMiddleware):
    """Carimba o IP do request p/ o audit() registrar (X-Forwarded-For primeiro)."""

    async def dispatch(self, request: Request, call_next):
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            ip = fwd.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else ""
        token = fixar_ip(ip)
        try:
            response = await call_next(request)
            if request.url.path == "/publico/extratos" or request.url.path.startswith("/organizacoes"):
                response.headers.update({"Cache-Control": "private, no-store", "X-Robots-Tag": "noindex, nofollow, noarchive", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"})
            return response
        finally:
            soltar_ip(token)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="RotaPay — Cobranças e conciliação",
              version="1.0.0",
              lifespan=lifespan,
              description="O RotaPay organiza as cobranças, os comprovantes e os pagamentos aos fornecedores")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(RateLimitMiddleware)
app.add_middleware(IPMiddleware)
app.add_middleware(PublicAmbienteMiddleware)

app.include_router(auth.r)
app.include_router(cadastro_publico.router)
app.include_router(interesse_lojas.router)
app.include_router(pessoas.r)
app.include_router(movimentacoes.r)
app.include_router(financeiro.rp)
app.include_router(financeiro.rl)
app.include_router(financeiro.rc)
app.include_router(financeiro.rs)
app.include_router(dashboard.r)
app.include_router(export.r)
app.include_router(links.r)
app.include_router(jobs.r)
app.include_router(webhooks.r)
app.include_router(comprovantes.r)
app.include_router(loja.r)
app.include_router(notas.r)
app.include_router(pagamentos.r)
app.include_router(acertos.r)
app.include_router(creditos.r)
app.include_router(extratos.r)


@app.get("/health")
def health():
    return {"ok": True}

app.include_router(intercambio.r)
app.include_router(cadastros_consulta.r)

app.include_router(configuracoes.r)

app.include_router(compartilhamentos_extratos.r)
app.include_router(legado.r)
app.include_router(visao_geral.r)

app.include_router(organizacoes.router)



@app.exception_handler(RequestValidationError)
async def validacao_entrada(request: Request, exc: RequestValidationError):
    if request.url.path.startswith("/organizacoes"):
        # Convites e senhas chegam pelo corpo; nunca repetir valores no erro.
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
            for e in exc.errors()]}, headers={"Cache-Control": "private, no-store"})
    return await request_validation_exception_handler(request, exc)

from .routers import fornecedores
app.include_router(fornecedores.router)
