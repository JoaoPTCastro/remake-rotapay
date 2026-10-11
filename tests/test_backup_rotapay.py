import json
import sqlite3
from pathlib import Path

import pytest

from scripts.backup_rotapay import BackupError, create_backup, restore_backup, verify_backup


@pytest.fixture
def source(tmp_path):
    central = tmp_path / "source" / "control.sqlite3"
    central.parent.mkdir()
    tenants = central.parent / "tenants"
    uploads = central.parent / "uploads"
    tenants.mkdir()
    uploads.mkdir()
    with sqlite3.connect(central) as db:
        db.executescript("CREATE TABLE ambientes_organizacao(organizacao_id INTEGER PRIMARY KEY, pronto BOOLEAN); INSERT INTO ambientes_organizacao VALUES(1,1),(2,1),(3,0);")
    with sqlite3.connect(tenants / "organizacao-2.sqlite3") as db:
        db.executescript("CREATE TABLE notas(id INTEGER PRIMARY KEY, valor NUMERIC); INSERT INTO notas VALUES(1,123.45);")
    (uploads / "organizacoes" / "2").mkdir(parents=True)
    (uploads / "organizacoes" / "2" / "comprovante.pdf").write_bytes(b"synthetic receipt")
    return central, tenants, uploads


def create(source, destination):
    return create_backup(*source, destination, operation_stopped=True)


def test_roundtrip_preserves_sources_and_private_permissions(source, tmp_path):
    before = {str(path): path.read_bytes() for root in source for path in ([root] if root.is_file() else root.rglob("*")) if path.is_file()}
    bundle, restored = tmp_path / "backup", tmp_path / "restored"
    manifest = create(source, bundle)
    assert manifest["tenant_ids"] == [2]
    assert verify_backup(bundle) == manifest
    assert restore_backup(bundle, restored, operation_stopped=True)["tenant_ids"] == manifest["tenant_ids"]
    with sqlite3.connect(restored / "tenants" / "organizacao-2.sqlite3") as db:
        assert db.execute("SELECT valor FROM notas").fetchone() == (123.45,)
    assert (restored / "uploads" / "organizacoes" / "2" / "comprovante.pdf").read_bytes() == b"synthetic receipt"
    assert all(Path(path).read_bytes() == content for path, content in before.items())
    for root in (bundle, restored):
        assert root.stat().st_mode & 0o777 == 0o700
        assert all(path.stat().st_mode & 0o777 == (0o700 if path.is_dir() else 0o600) for path in root.rglob("*"))


def test_requires_offline_confirmation(source, tmp_path):
    with pytest.raises(BackupError, match="parada"):
        create_backup(*source, tmp_path / "backup")
    create(source, tmp_path / "backup")
    with pytest.raises(BackupError, match="parada"):
        restore_backup(tmp_path / "backup", tmp_path / "restore")
    assert not (tmp_path / "restore").exists()


def test_missing_ready_tenant_fails_without_partial_bundle(source, tmp_path):
    (source[1] / "organizacao-2.sqlite3").unlink()
    with pytest.raises(BackupError, match="ausente"):
        create(source, tmp_path / "backup")
    assert not (tmp_path / "backup").exists()


def test_does_not_overwrite_destinations(source, tmp_path):
    bundle = tmp_path / "backup"
    create(source, bundle)
    with pytest.raises(BackupError, match="novo"):
        create(source, bundle)
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "marker").write_text("preserve")
    with pytest.raises(BackupError, match="novo"):
        restore_backup(bundle, existing, operation_stopped=True)
    assert (existing / "marker").read_text() == "preserve"


@pytest.mark.parametrize("name", ["uploads/altered.pdf", "central.sqlite3"])
def test_tampering_rejected_before_restore(source, tmp_path, name):
    bundle = tmp_path / "backup"
    create(source, bundle)
    (bundle / name).write_bytes(b"altered")
    with pytest.raises(BackupError):
        restore_backup(bundle, tmp_path / "restored", operation_stopped=True)
    assert not (tmp_path / "restored").exists()


@pytest.mark.parametrize("unsafe", ["../escape", "/tmp/escape", "uploads/../../escape", "uploads\\escape"])
def test_manifest_path_traversal_rejected(source, tmp_path, unsafe):
    bundle = tmp_path / "backup"
    create(source, bundle)
    manifest_file = bundle / "manifest.json"
    manifest = json.loads(manifest_file.read_text())
    manifest["files"][unsafe] = {"sha256": "0" * 64, "size": 0}
    manifest_file.write_text(json.dumps(manifest))
    with pytest.raises(BackupError, match="inseguro"):
        verify_backup(bundle)


def test_symlink_source_and_bundle_rejected(source, tmp_path):
    (source[2] / "linked").symlink_to(source[0])
    with pytest.raises(BackupError, match="simbólico"):
        create(source, tmp_path / "backup")
    (source[2] / "linked").unlink()
    create(source, tmp_path / "backup")
    (tmp_path / "backup" / "uploads" / "linked").symlink_to(source[0])
    with pytest.raises(BackupError, match="simbólico"):
        verify_backup(tmp_path / "backup")


def test_destination_within_source_rejected(source):
    with pytest.raises(BackupError, match="origem"):
        create(source, source[2] / "backup")


def test_secret_configuration_is_not_copied(source, tmp_path):
    (source[2] / ".env.local").write_text("SECRET=synthetic")
    with pytest.raises(BackupError, match="configuração"):
        create(source, tmp_path / "backup")
    assert not (tmp_path / "backup").exists()


def test_foreign_key_corruption_rejected(source, tmp_path):
    with sqlite3.connect(source[1] / "organizacao-2.sqlite3") as db:
        db.executescript("CREATE TABLE child(parent_id INTEGER REFERENCES notas(id)); INSERT INTO child VALUES(99);")
    with pytest.raises(BackupError, match="referências"):
        create(source, tmp_path / "backup")
    assert not (tmp_path / "backup").exists()


def test_restore_rebases_attachment_paths_without_using_original_files(source, tmp_path):
    old = source[2] / "organizacoes" / "2" / "comprovante.pdf"
    database = source[1] / "organizacao-2.sqlite3"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE pagamento_anexos(id INTEGER PRIMARY KEY, arquivo_path TEXT)")
        db.execute("INSERT INTO pagamento_anexos VALUES(1, ?)", (str(old),))
    bundle, restored = tmp_path / "backup", tmp_path / "restored"
    create(source, bundle)
    old.unlink()
    restore_backup(bundle, restored, operation_stopped=True)
    new = restored / "uploads" / "organizacoes" / "2" / "comprovante.pdf"
    with sqlite3.connect(restored / "tenants" / "organizacao-2.sqlite3") as db:
        assert db.execute("SELECT arquivo_path FROM pagamento_anexos").fetchone() == (str(new),)
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT arquivo_path FROM pagamento_anexos").fetchone() == (str(old),)
    assert new.read_bytes() == b"synthetic receipt"
    verify_backup(restored)


def test_attachment_from_other_organization_fails_closed(source, tmp_path):
    other = source[2] / "organizacoes" / "3" / "receipt.pdf"
    other.parent.mkdir()
    other.write_bytes(b"other store")
    with sqlite3.connect(source[1] / "organizacao-2.sqlite3") as db:
        db.execute("CREATE TABLE comprovantes(id INTEGER PRIMARY KEY, arquivo_path TEXT)")
        db.execute("INSERT INTO comprovantes VALUES(1, ?)", (str(other),))
    with pytest.raises(BackupError, match="outra organização"):
        create(source, tmp_path / "backup")
    assert not (tmp_path / "backup").exists()


def test_missing_referenced_attachment_fails_closed(source, tmp_path):
    with sqlite3.connect(source[1] / "organizacao-2.sqlite3") as db:
        db.execute("CREATE TABLE nota_anexos(id INTEGER PRIMARY KEY, arquivo_path TEXT)")
        db.execute("INSERT INTO nota_anexos VALUES(1, ?)", (str(source[2] / "organizacoes" / "2" / "missing.pdf"),))
    with pytest.raises(BackupError, match="ausente"):
        create(source, tmp_path / "backup")
    assert not (tmp_path / "backup").exists()


def test_bundle_is_independent_of_replaced_original_symlinks(source, tmp_path):
    old = source[2] / "organizacoes" / "2" / "comprovante.pdf"
    database = source[1] / "organizacao-2.sqlite3"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE comprovantes(arquivo_path TEXT)")
        db.execute("INSERT INTO comprovantes VALUES(?)", (str(old),))
    bundle = tmp_path / "backup"
    create(source, bundle)
    old.unlink()
    old.symlink_to(tmp_path / "unrelated-and-missing")
    verify_backup(bundle)
    restore_backup(bundle, tmp_path / "restored", operation_stopped=True)
    assert (tmp_path / "restored" / "uploads" / "organizacoes" / "2" / "comprovante.pdf").read_bytes() == b"synthetic receipt"


def test_relative_legacy_attachment_is_normalized_in_copy_only(source, tmp_path, monkeypatch):
    monkeypatch.chdir(source[0].parent)
    raw = "uploads/organizacoes/2/comprovante.pdf"
    database = source[1] / "organizacao-2.sqlite3"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE comprovantes(arquivo_path TEXT)")
        db.execute("INSERT INTO comprovantes VALUES(?)", (raw,))
    bundle = tmp_path / "backup"
    create(source, bundle)
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT arquivo_path FROM comprovantes").fetchone() == (raw,)
    monkeypatch.chdir(tmp_path)
    restored = tmp_path / "restored"
    restore_backup(bundle, restored, operation_stopped=True)
    with sqlite3.connect(restored / "tenants" / "organizacao-2.sqlite3") as db:
        assert db.execute("SELECT arquivo_path FROM comprovantes").fetchone() == (str(restored / raw),)


def test_logo_missing_or_removed_from_manifest_fails_closed(source, tmp_path):
    central, _, uploads = source
    with sqlite3.connect(central) as db:
        db.executescript("CREATE TABLE loja(id INTEGER PRIMARY KEY, logo_arquivo TEXT); INSERT INTO loja VALUES(1,'logo.png');")
    with pytest.raises(BackupError, match="ausente"):
        create(source, tmp_path / "missing")
    (uploads / "loja-logos").mkdir()
    (uploads / "loja-logos" / "logo.png").write_bytes(b"synthetic logo")
    bundle = tmp_path / "backup"
    create(source, bundle)
    manifest = json.loads((bundle / "manifest.json").read_text())
    del manifest["files"]["uploads/loja-logos/logo.png"]
    (bundle / "uploads" / "loja-logos" / "logo.png").unlink()
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(BackupError, match="Logo"):
        verify_backup(bundle)


def test_logo_roundtrip_uses_organization_directory(source, tmp_path):
    with sqlite3.connect(source[1] / "organizacao-2.sqlite3") as db:
        db.executescript("CREATE TABLE loja(id INTEGER PRIMARY KEY, logo_arquivo TEXT); INSERT INTO loja VALUES(1,'logo.png');")
    path = source[2] / "organizacoes" / "2" / "loja-logos" / "logo.png"
    path.parent.mkdir()
    path.write_bytes(b"synthetic tenant logo")
    create(source, tmp_path / "backup")
    restored = tmp_path / "restored"
    restore_backup(tmp_path / "backup", restored, operation_stopped=True)
    assert (restored / "uploads" / "organizacoes" / "2" / "loja-logos" / "logo.png").read_bytes() == path.read_bytes()
    with sqlite3.connect(restored / "tenants" / "organizacao-2.sqlite3") as db:
        assert db.execute("SELECT logo_arquivo FROM loja").fetchone() == ("logo.png",)


def test_logo_path_cannot_escape_uploads(source, tmp_path):
    with sqlite3.connect(source[0]) as db:
        db.executescript("CREATE TABLE loja(id INTEGER PRIMARY KEY, logo_arquivo TEXT); INSERT INTO loja VALUES(1,'../private.png');")
    with pytest.raises(BackupError, match="logo"):
        create(source, tmp_path / "backup")
    assert not (tmp_path / "backup").exists()
