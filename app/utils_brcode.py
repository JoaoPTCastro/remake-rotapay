"""Payload PIX copia e cola (BR Code / EMVCo) gerado localmente, sem banco.

Usado nos links de valor aberto ou sem cobrança Checkto: o pagador cola
o código no app do banco. Segue o padrão BR Code do Banco Central:
GUI "BR.GOV.BCB.PIX", moeda 986 (BRL), CRC16-CCITT-FALSE no campo 63.
"""
import re
import unicodedata


def crc16_ccitt(dados: bytes) -> int:
    """CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF."""
    crc = 0xFFFF
    for b in dados:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def _campo(fid: str, valor: str) -> str:
    return f"{fid}{len(valor):02d}{valor}"


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn")


def _txid(txid: str) -> str:
    limpo = re.sub(r"[^a-zA-Z0-9]", "", txid or "")
    return limpo[:25] or "***"


def payload_copia_cola(chave: str, nome: str, cidade: str = "BRASIL",
                       valor: float | None = None, txid: str = "***") -> str:
    """Monta o BR Code. Valor None = QR dinâmico/valor aberto (sem campo 54)."""
    if not chave:
        raise ValueError("chave PIX vazia")
    chave = chave.strip()
    nome = _sem_acento(nome).upper()[:25] or "LOJA"
    cidade = _sem_acento(cidade).upper()[:15] or "BRASIL"
    conta = _campo("00", "BR.GOV.BCB.PIX") + _campo("01", chave)
    base = (_campo("00", "01") + _campo("26", conta) + _campo("52", "0000") +
            _campo("53", "986"))
    if valor is not None:
        if valor <= 0:
            raise ValueError("valor deve ser positivo")
        base += _campo("54", f"{valor:.2f}")
    base += (_campo("58", "BR") + _campo("59", nome) + _campo("60", cidade) +
             _campo("62", _campo("05", _txid(txid))) + "6304")
    return base + f"{crc16_ccitt(base.encode()):04X}"
