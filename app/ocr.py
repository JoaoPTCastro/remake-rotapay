"""Sprint C: simulação de OCR experimental + sugestão de fornecedor.

Esta implementação não lê o comprovante: simula a extração (valor, data,
remetente, destinatário, chave) a partir dos dados da movimentação vinculada.
Um OCR real pode entrar no mesmo ponto (`extrair()`), sem mudar o contrato:
devolve dict + confiança.
Sugestão nunca concilia sozinha; só propõe para revisão humana.
"""
import json
import re


def _norm(s: str) -> str:
    s = (s or "").upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def extrair(mov_valor: float, mov_data: str, remetente: str,
            destinatario: str, chave_hint: str = "") -> dict:
    """Contrato experimental simulado: campos + confiança por campo (0..1)."""
    return {
        "valor": {"valor": round(mov_valor, 2), "confianca": 0.80},
        "data": {"valor": mov_data, "confianca": 0.80},
        "remetente": {"valor": remetente or "", "confianca": 0.70},
        "destinatario": {"valor": destinatario or "", "confianca": 0.70},
        "chave": {"valor": chave_hint, "confianca": 0.50 if chave_hint else 0.0},
    }


def sugerir_fornecedor(remetente: str, candidatos: list[tuple[int, str]]) -> tuple[int | None, str]:
    """Match conservador: primeiras 2 palavras do remetente contidas no nome.

    Retorna (fornecedor_id, motivo) ou (None, '').
    """
    R = _norm(remetente).split()
    if len(R) < 2:
        return None, ""
    alvo = " ".join(R[:2])
    for fid, nome in candidatos:
        if alvo and alvo in _norm(nome):
            return fid, f"remetente '{remetente}' casa com '{nome}'"
    return None, ""


def dumps(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False)
