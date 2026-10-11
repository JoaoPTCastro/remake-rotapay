"""Backup offline do RotaPay. Não use com a operação em andamento."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
from contextlib import contextmanager, closing
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


class BackupError(ValueError):
    """Entrada ou pacote inválido; nenhum banco operacional deve ser sobrescrito."""


def _source(path: str | Path, *, directory: bool = False) -> Path:
    path = Path(path).absolute()
    if any(part.is_symlink() for part in [path, *path.parents]):
        raise BackupError("Links simbólicos não são permitidos.")
    if not (path.is_dir() if directory else path.is_file()):
        raise BackupError(f"Origem ausente ou inválida: {path.name}")
    return path.resolve()


def _destination(path: str | Path, sources: list[Path]) -> Path:
    target = Path(path).absolute()
    if any(part.is_symlink() for part in [target, *target.parents]):
        raise BackupError("Destino com link simbólico não é permitido.")
    target = target.resolve()
    if target.exists():
        raise BackupError("O destino deve ser novo e não pode existir.")
    for source in sources:
        if target == source or target.is_relative_to(source) or source.is_relative_to(target):
            raise BackupError("Destino não pode conter nem estar dentro de uma origem.")
    return target


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@contextmanager
def _connect(path: Path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
        yield connection


def _check_database(path: Path) -> None:
    with _connect(path) as db:
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise BackupError("Banco com integridade inválida.")
        if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise BackupError("Banco contém referências inválidas.")


def _tenant_ids(central: Path) -> list[int]:
    with _connect(central) as db:
        try:
            rows = db.execute("SELECT organizacao_id FROM ambientes_organizacao WHERE pronto = 1").fetchall()
        except sqlite3.OperationalError as error:
            raise BackupError("Cadastro de ambientes não encontrado.") from error
    ids = []
    for (identifier,) in rows:
        if not isinstance(identifier, int) or identifier < 1:
            raise BackupError("Identificador de ambiente inválido.")
        if identifier != 1:
            ids.append(identifier)
    return sorted(set(ids))


def _private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=False, mode=0o700)
    path.chmod(0o700)


def _parent_private(path: Path, root: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    for directory in [path, *path.parents]:
        if directory == root:
            break
        directory.chmod(0o700)


_ATTACHMENT_TABLES = ("comprovantes", "nota_anexos", "pagamento_anexos")


def _logo_refs(database: Path, organization: int) -> list[Path]:
    with _connect(database) as db:
        columns = {row[1] for row in db.execute("PRAGMA table_info(loja)")}
        if "logo_arquivo" not in columns:
            return []
        names = db.execute("SELECT logo_arquivo FROM loja WHERE logo_arquivo IS NOT NULL AND logo_arquivo != ''").fetchall()
    root = Path("loja-logos") if organization == 1 else Path("organizacoes") / str(organization) / "loja-logos"
    references = []
    for (name,) in names:
        if not isinstance(name, str) or name in (".", "..") or "/" in name or "\\" in name:
            raise BackupError("Referência de logo inválida.")
        references.append(root / name)
    return references


def _attachment_refs(database: Path, uploads: Path, organization: int, *, live_source: bool = False) -> list[tuple[str, str, Path]]:
    references = []
    allowed = uploads if organization == 1 else uploads / "organizacoes" / str(organization)
    with _connect(database) as db:
        existing = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in _ATTACHMENT_TABLES:
            if table not in existing:
                continue
            for (raw,) in db.execute(f"SELECT arquivo_path FROM {table} WHERE arquivo_path IS NOT NULL AND arquivo_path != ''"):
                if not isinstance(raw, str):
                    raise BackupError("Referência de anexo inválida.")
                path = Path(os.path.abspath(raw))
                if live_source:
                    if any(part.is_symlink() for part in [path, *path.parents]):
                        raise BackupError("Anexo com link simbólico não é permitido.")
                    path = path.resolve()
                elif not Path(raw).is_absolute():
                    raise BackupError("Referência relativa não normalizada no pacote.")
                if not path.is_relative_to(allowed) or (organization == 1 and path.is_relative_to(uploads / "organizacoes")):
                    raise BackupError("Anexo pertence a outra organização ou origem.")
                references.append((table, raw, path.relative_to(uploads)))
    return references


def _copy_database(source: Path, destination: Path) -> None:
    _check_database(source)
    with _connect(source) as original, closing(sqlite3.connect(destination)) as copy:
        original.backup(copy)
    destination.chmod(0o600)
    _check_database(destination)


def _files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise BackupError("Pacote/origem contém link simbólico.")
        if path.is_file():
            files.append(path)
        elif not path.is_dir():
            raise BackupError("Arquivo especial não permitido.")
    return sorted(files)


def create_backup(central_db: str | Path, tenant_dir: str | Path,
                  uploads_dir: str | Path, destination: str | Path, *,
                  operation_stopped: bool = False) -> dict:
    if not operation_stopped:
        raise BackupError("Confirme que a operação está parada; o backup entre bancos não é atômico ao vivo.")
    central = _source(central_db)
    tenants = _source(tenant_dir, directory=True)
    uploads = _source(uploads_dir, directory=True)
    target = _destination(destination, [central, tenants, uploads])
    ids = _tenant_ids(central)
    tenant_sources = [(identifier, _source(tenants / f"organizacao-{identifier}.sqlite3")) for identifier in ids]
    upload_files = _files(uploads)
    for identifier, database in [(1, central), *tenant_sources]:
        for _, _, relative in _attachment_refs(database, uploads, identifier, live_source=True):
            _source(uploads / relative)
        for relative in _logo_refs(database, identifier):
            _source(uploads / relative)
    # Somente arquivos do diretório explícito de uploads; segredos/configurações são recusados.
    if any(path.name.startswith(".env") or path.suffix in {".sqlite3", ".db"} for path in upload_files):
        raise BackupError("Uploads contém configuração ou banco; revise a origem.")
    _private_directory(target)
    try:
        _private_directory(target / "tenants")
        _private_directory(target / "uploads")
        _copy_database(central, target / "central.sqlite3")
        for identifier, source in tenant_sources:
            _copy_database(source, target / "tenants" / f"organizacao-{identifier}.sqlite3")
        # Canonicalize legacy relative references in copied databases only, so the
        # package no longer depends on the API working directory during restore.
        for identifier, source in [(1, central), *tenant_sources]:
            copy = target / "central.sqlite3" if identifier == 1 else target / "tenants" / f"organizacao-{identifier}.sqlite3"
            with closing(sqlite3.connect(copy)) as db, db:
                for table, raw, relative in _attachment_refs(source, uploads, identifier, live_source=True):
                    db.execute(f"UPDATE {table} SET arquivo_path = ? WHERE arquivo_path = ?", (str(uploads / relative), raw))
        for source in upload_files:
            output = target / "uploads" / source.relative_to(uploads)
            _parent_private(output.parent, target)
            shutil.copyfile(source, output)
            output.chmod(0o600)
        manifest = {"version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
                    "mode": "offline", "source_uploads_root": str(uploads), "tenant_ids": ids, "files": {
                        path.relative_to(target).as_posix(): {"sha256": _hash(path), "size": path.stat().st_size}
                        for path in _files(target)}}
        manifest_path = target / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest_path.chmod(0o600)
        verify_backup(target)
        return manifest
    except Exception:
        shutil.rmtree(target)
        raise


def verify_backup(bundle: str | Path) -> dict:
    root = _source(bundle, directory=True)
    files = _files(root)
    try:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise BackupError("Manifesto ausente ou inválido.") from error
    if not isinstance(manifest, dict) or (type(manifest.get("version")) is not int or manifest.get("version") != 1) or manifest.get("mode") != "offline":
        raise BackupError("Versão ou modo de backup inválido.")
    entries = manifest.get("files")
    ids = manifest.get("tenant_ids")
    if not isinstance(entries, dict) or not isinstance(ids, list) or any(type(identifier) is not int or identifier < 2 for identifier in ids) or ids != sorted(set(ids)):
        raise BackupError("Manifesto inválido.")
    expected_databases = {"central.sqlite3", *(f"tenants/organizacao-{identifier}.sqlite3" for identifier in ids)}
    for name, metadata in entries.items():
        if not isinstance(name, str):
            raise BackupError("Caminho inválido no manifesto.")
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name or path.as_posix() != name or name == "manifest.json":
            raise BackupError("Caminho inseguro no manifesto.")
        if name not in expected_databases and not name.startswith("uploads/"):
            raise BackupError("Arquivo não permitido no manifesto.")
        if name.startswith("uploads/") and (path.name.startswith(".env") or path.suffix in {".sqlite3", ".db"}):
            raise BackupError("Configuração ou banco não permitido em uploads.")
        if not isinstance(metadata, dict):
            raise BackupError("Metadados inválidos.")
        if type(metadata.get("size")) is not int or metadata["size"] < 0 or not isinstance(metadata.get("sha256"), str):
            raise BackupError("Metadados inválidos.")
        local = _source(root / name)
        if metadata.get("sha256") != _hash(local) or metadata.get("size") != local.stat().st_size:
            raise BackupError("Arquivo alterado ou incompleto.")
    actual = {path.relative_to(root).as_posix() for path in files} - {"manifest.json"}
    if actual != set(entries) or not expected_databases.issubset(actual):
        raise BackupError("Arquivos extras ou ausentes no pacote.")
    source_uploads = manifest.get("source_uploads_root")
    if not isinstance(source_uploads, str) or not Path(source_uploads).is_absolute():
        raise BackupError("Origem dos anexos inválida no manifesto.")
    for name in expected_databases:
        _check_database(root / name)
        organization = 1 if name == "central.sqlite3" else int(Path(name).stem.removeprefix("organizacao-"))
        for _, _, relative in _attachment_refs(root / name, Path(source_uploads), organization):
            if "uploads/" + relative.as_posix() not in entries:
                raise BackupError("Anexo referenciado está ausente do pacote.")
        for relative in _logo_refs(root / name, organization):
            if "uploads/" + relative.as_posix() not in entries:
                raise BackupError("Logo referenciado está ausente do pacote.")
    if _tenant_ids(root / "central.sqlite3") != ids:
        raise BackupError("Ambientes divergem do cadastro central.")
    return manifest


def restore_backup(bundle: str | Path, destination: str | Path, *,
                   operation_stopped: bool = False) -> dict:
    if not operation_stopped:
        raise BackupError("Confirme que a operação está parada antes de preparar a restauração.")
    root = _source(bundle, directory=True)
    manifest = verify_backup(root)
    target = _destination(destination, [root])
    _private_directory(target)
    try:
        for source in _files(root):
            output = target / source.relative_to(root)
            _parent_private(output.parent, target)
            shutil.copyfile(source, output)
            output.chmod(0o600)
        old_uploads = Path(manifest["source_uploads_root"])
        for organization, database in [(1, target / "central.sqlite3"), *[(identifier, target / "tenants" / f"organizacao-{identifier}.sqlite3") for identifier in manifest["tenant_ids"]]]:
            references = _attachment_refs(database, old_uploads, organization)
            with closing(sqlite3.connect(database)) as db, db:
                for table, raw, relative in references:
                    db.execute(f"UPDATE {table} SET arquivo_path = ? WHERE arquivo_path = ?", (str(target / "uploads" / relative), raw))
        restored_manifest = dict(manifest)
        restored_manifest["source_uploads_root"] = str(target / "uploads")
        restored_manifest["files"] = {name: {"sha256": _hash(target / name), "size": (target / name).stat().st_size} for name in manifest["files"]}
        (target / "manifest.json").write_text(json.dumps(restored_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        verify_backup(target)
        return restored_manifest
    except Exception:
        shutil.rmtree(target)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup offline: pare a API e os demais escritores antes de criar/restaurar. Não oferece atomicidade entre bancos em operação.")
    actions = parser.add_subparsers(dest="action", required=True)
    create = actions.add_parser("criar")
    for name in ("central", "ambientes", "uploads", "destino"):
        create.add_argument(f"--{name}", required=True)
    create.add_argument("--operacao-parada", action="store_true")
    verify = actions.add_parser("verificar")
    verify.add_argument("--pacote", required=True)
    restore = actions.add_parser("restaurar", help="Prepara somente diretório novo; não substitui bancos operacionais.")
    restore.add_argument("--pacote", required=True)
    restore.add_argument("--destino", required=True)
    restore.add_argument("--operacao-parada", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "criar":
            result = create_backup(args.central, args.ambientes, args.uploads, args.destino, operation_stopped=args.operacao_parada)
        elif args.action == "restaurar":
            result = restore_backup(args.pacote, args.destino, operation_stopped=args.operacao_parada)
        else:
            result = verify_backup(args.pacote)
    except (BackupError, OSError, sqlite3.Error) as error:
        parser.exit(1, f"Falha: {error}\n")
    print(json.dumps({"status": "verificado", "tenant_ids": result["tenant_ids"], "files": len(result["files"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
