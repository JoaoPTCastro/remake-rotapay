"""Contexto publico explicito e arquivos privados nunca herdam outra loja."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from app.routers import links, loja, movimentacoes


def session(org):
    return SimpleNamespace(info={"organizacao_id": org})


def test_link_nova_loja_identifica_ambiente_sem_alterar_compatibilidade():
    link = SimpleNamespace(id=8, token="segredo", representante_id=1, fornecedor_id=2,
        valor_fixo=100, ativo=True, pix_code=None)
    db = Mock(info={"organizacao_id": 2})
    db.get.return_value = SimpleNamespace(nome="Nome")
    assert links._out(link, db)["url"] == "/v/2/segredo"
    db.info["organizacao_id"] = 1
    assert links._out(link, db)["url"] == "/v/segredo"


def test_nova_loja_nao_chama_checkto_com_credenciais_globais(monkeypatch):
    criar = Mock(side_effect=AssertionError("Chamada externa proibida"))
    monkeypatch.setattr("app.checkto.criar_cobranca_pix", criar)
    with pytest.raises(HTTPException) as erro:
        links._gerar_cobranca(session(2), SimpleNamespace(valor_fixo=100), None)
    assert erro.value.status_code == 503
    criar.assert_not_called()


def test_logo_usa_raiz_da_loja_e_mantem_raiz_legada(tmp_path, monkeypatch):
    monkeypatch.setattr(loja, "UPLOAD_DIR", str(tmp_path))
    assert loja._logo_root(session(1)) == tmp_path / "loja-logos"
    assert loja._logo_root(session(2)) == tmp_path / "organizacoes" / "2" / "loja-logos"


@pytest.mark.parametrize("router, campo, metodo", [
    (movimentacoes, "comprovante_path", "baixar"),
])
def test_download_rejeita_arquivo_de_outra_loja_e_symlink(tmp_path, monkeypatch, router, campo, metodo):
    monkeypatch.setattr(router, "UPLOAD_DIR", str(tmp_path))
    outro = tmp_path / "arquivo-legado.pdf"
    outro.write_bytes(b"%PDF-1.4")
    db = Mock(info={"organizacao_id": 2})
    db.get.return_value = SimpleNamespace(**{campo: str(outro)})
    with pytest.raises(HTTPException) as erro:
        getattr(router, metodo)(1, db, None)
    assert erro.value.status_code == 404
    raiz = tmp_path / "organizacoes" / "2"
    raiz.mkdir(parents=True)
    atalho = raiz / "atalho.pdf"
    atalho.symlink_to(outro)
    setattr(db.get.return_value, campo, str(atalho))
    with pytest.raises(HTTPException) as erro:
        getattr(router, metodo)(1, db, None)
    assert erro.value.status_code == 404
    local = raiz / "local.pdf"
    local.write_bytes(b"%PDF-1.4")
    setattr(db.get.return_value, campo, str(local))
    assert str(getattr(router, metodo)(1, db, None).path) == str(local)


@pytest.mark.parametrize("router, campo, metodo", [
    (movimentacoes, "comprovante_path", "baixar"),
])
def test_raiz_legada_nao_permite_subdiretorio_de_nova_loja(tmp_path, monkeypatch, router, campo, metodo):
    monkeypatch.setattr(router, "UPLOAD_DIR", str(tmp_path))
    path = tmp_path / "organizacoes" / "2" / "privado.pdf"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"%PDF-1.4")
    db = Mock(info={"organizacao_id": 1})
    db.get.return_value = SimpleNamespace(**{campo: str(path)})
    with pytest.raises(HTTPException) as erro:
        getattr(router, metodo)(1, db, None)
    assert erro.value.status_code == 404
