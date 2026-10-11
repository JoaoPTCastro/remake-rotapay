"""IP encaminhado apenas pelo proxy interno autenticado; nunca pelo navegador."""
import hmac
import ipaddress
import os
from fastapi import HTTPException, Request


def client_ip(request: Request):
    expected = os.getenv('PRIVATE_PROXY_KEY', '')
    supplied = request.headers.get('X-RotaPay-Proxy-Key', '')
    if expected and supplied and hmac.compare_digest(expected, supplied):
        try:
            return str(ipaddress.ip_address(request.headers.get('X-RotaPay-Client-IP', '')))
        except ValueError:
            raise HTTPException(400, 'Origem inválida')
    return request.client.host if request.client else '?'
