"""BR Code local: CRC conhecido + propriedades estruturais do payload."""
import pytest

from app.utils_brcode import crc16_ccitt, payload_copia_cola


def test_crc16_vetor_conhecido():
    # Vetor padrão do CRC-16/CCITT-FALSE ("123456789" -> 0x29B1).
    assert crc16_ccitt(b"123456789") == 0x29B1


def test_payload_estrutura_e_crc():
    p = payload_copia_cola("chave@teste.com", "Loja Demo", "Sao Paulo",
                           valor=100, txid="link-abc 123")
    assert p.startswith("000201")
    assert "BR.GOV.BCB.PIX" in p
    assert "chave@teste.com" in p
    assert "986" in p
    assert "5406100.00" in p  # campo 54: id 54 + tam 06 + valor
    assert "linkabc123" in p  # txid sanitizado (sem hífen/espaço)
    assert "SAO PAULO" in p  # sem acento, maiúsculo
    corpo, crc = p[:-4], p[-4:]
    assert crc == f"{crc16_ccitt(corpo.encode()):04X}"


def test_payload_valor_aberto_sem_campo_54():
    p = payload_copia_cola("+5511999999999", "Fulano de Tal com Nome Bem Longo Demais")
    assert "54" not in p[:60]  # sem valor fixo
    assert "FULANO DE TAL COM NOME BE" in p  # nome truncado em 25
    assert p.endswith(p[-4:]) and len(p[-4:]) == 4


def test_payload_recusa_chave_vazia_e_valor_invalido():
    with pytest.raises(ValueError):
        payload_copia_cola("", "Loja")
    with pytest.raises(ValueError):
        payload_copia_cola("a@b.com", "Loja", valor=0)
