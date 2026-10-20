#!/usr/bin/env python3
"""Runtime Linux nativo e portátil para o Redmine ReqSys.

Não provisiona host, não publica ambiente e não manipula secrets remotos.
Instala releases imutáveis, separa estado persistente e produz backup/restore
verificável para SQLite. PostgreSQL pode ser usado pelo serviço via DATABASE_URL,
mas o backup/restore PostgreSQL permanece um gate separado.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
from typing import Iterable

REPOSITORY = "ericson-j-santos/redmine"
RELEASE_MANIFEST = Path("public/reqsys-e2e/release-manifest.json")
NATIVE_METADATA = Path(".reqsys-native-release.json")
SCHEMA_VERSION = 1
MAX_JSON_BYTES = 2_000_000
STATE_NAMES = ("db", "files", "config", "tmp", "log", "backups")
EXCLUDED_TOP = {
    ".git", ".bundle", ".runtime", "coverage", "files", "log", "tmp", "vendor",
}
EXCLUDED_TREE = {
    "files", "log", "tmp", "vendor/bundle",
    "config/initializers/secret_token.rb",
}
ASSET_AUTOCOMPILE_ON = b"config.assets.redmine_detect_update = true"
ASSET_AUTOCOMPILE_OFF = b"config.assets.redmine_detect_update = false"

START_SCRIPT = r'''#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "${ROOT}"
: "${DATABASE_URL:?DATABASE_URL_REQUIRED}"
export RAILS_ENV=production
export BUNDLE_GEMFILE="${ROOT}/Gemfile"
export BUNDLE_PATH="${ROOT}/vendor/bundle"
export BUNDLE_DEPLOYMENT=true
export BUNDLE_FROZEN=true
export BUNDLE_WITHOUT="development:test"
bind="${REDMINE_BIND:-127.0.0.1}"
port="${REDMINE_PORT:-3000}"
exec bundle exec puma -w 0 -b "tcp://${bind}:${port}" -e production
'''


class NativeRuntimeError(ValueError):
    """Erro estável e sanitizado."""


def validate_service_shutdown(ready: bool, terminated_by_test: bool, returncode: int | None) -> None:
    """Mantém a causa de readiness e aceita SIGTERM só quando iniciado pelo teste."""
    if not ready:
        raise NativeRuntimeError("NATIVE_E2E_HTTP_NOT_READY")
    if not terminated_by_test:
        raise NativeRuntimeError("NATIVE_E2E_SERVICE_EXITED_BEFORE_STOP")
    clean = (0, -signal.SIGTERM, 128 + signal.SIGTERM)
    if type(returncode) is not int or returncode not in clean:
        raise NativeRuntimeError("NATIVE_E2E_SERVICE_EXIT_INVALID")


def _sha(value: object, length: int = 40) -> str:
    if not isinstance(value, str) or not re.fullmatch(rf"[0-9a-f]{{{length}}}", value):
        raise NativeRuntimeError("NATIVE_SHA_INVALID")
    return value


def _safe_root(path: Path, *, must_exist: bool = True) -> Path:
    path = Path(path)
    if not path.is_absolute():
        raise NativeRuntimeError("NATIVE_ROOT_NOT_ABSOLUTE")
    if path.exists() and path.is_symlink():
        raise NativeRuntimeError("NATIVE_ROOT_SYMLINK_REJECTED")
    if must_exist and not path.is_dir():
        raise NativeRuntimeError("NATIVE_ROOT_UNAVAILABLE")
    if path.exists() and path.resolve() != path:
        raise NativeRuntimeError("NATIVE_ROOT_NOT_CANONICAL")
    return path


def _read_json(path: Path) -> dict:
    try:
        raw = path.read_bytes()
    except OSError:
        raise NativeRuntimeError("NATIVE_JSON_UNAVAILABLE") from None
    if len(raw) > MAX_JSON_BYTES:
        raise NativeRuntimeError("NATIVE_JSON_TOO_LARGE")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise NativeRuntimeError("NATIVE_JSON_DUPLICATE_KEY")
            result[key] = value
        return result

    try:
        data = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError):
        raise NativeRuntimeError("NATIVE_JSON_INVALID") from None
    if not isinstance(data, dict):
        raise NativeRuntimeError("NATIVE_JSON_INVALID")
    return data


def _canonical_json(data: object) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _hash_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise NativeRuntimeError("NATIVE_FILE_INVALID")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        raise NativeRuntimeError("NATIVE_FILE_UNAVAILABLE") from None
    return digest.hexdigest()


def _relative_files(root: Path, *, exclude: Iterable[str] = ()) -> list[Path]:
    excluded = set(exclude)
    result: list[Path] = []
    for path in sorted(root.rglob("*"), key=lambda value: value.as_posix()):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            if rel in EXCLUDED_TREE:
                continue
            raise NativeRuntimeError("NATIVE_SYMLINK_REJECTED")
        if any(rel == item or rel.startswith(item + "/") for item in excluded):
            continue
        if path.is_file():
            result.append(path)
    return result


def _tree_hash(root: Path) -> str:
    entries = {}
    for path in _relative_files(root, exclude=EXCLUDED_TREE):
        rel = path.relative_to(root).as_posix()
        if rel == NATIVE_METADATA.as_posix():
            continue
        entries[rel] = _hash_file(path)
    return hashlib.sha256(_canonical_json(entries)).hexdigest()


def verify_source_manifest(source: Path, expected_sha: str) -> dict:
    source = _safe_root(source)
    expected_sha = _sha(expected_sha)
    manifest = _read_json(source / RELEASE_MANIFEST)
    identity = manifest.get("source_identity")
    if (
        manifest.get("schema_version") != 1
        or not isinstance(identity, dict)
        or identity.get("repository") != REPOSITORY
        or _sha(identity.get("source_sha")) != expected_sha
    ):
        raise NativeRuntimeError("NATIVE_SOURCE_IDENTITY_MISMATCH")
    artifacts = manifest.get("artifacts_sha256")
    if not isinstance(artifacts, dict) or not artifacts:
        raise NativeRuntimeError("NATIVE_SOURCE_ARTIFACTS_MISSING")
    for rel, expected in artifacts.items():
        if (
            not isinstance(rel, str)
            or rel.startswith("/")
            or ".." in Path(rel).parts
            or not re.fullmatch(r"[0-9a-f]{64}", str(expected))
        ):
            raise NativeRuntimeError("NATIVE_SOURCE_ARTIFACT_INVALID")
        if _hash_file(source / rel) != expected:
            raise NativeRuntimeError("NATIVE_SOURCE_ARTIFACT_MISMATCH")
    if manifest.get("evidence_scope") != "isolated_build_not_post_deploy_or_pc24x7":
        raise NativeRuntimeError("NATIVE_SOURCE_SCOPE_INVALID")
    return manifest


def _copy_release(source: Path, staging: Path) -> None:
    def ignore(directory: str, names: list[str]):
        if Path(directory).resolve() == source:
            return [name for name in names if name in EXCLUDED_TOP]
        return []

    try:
        shutil.copytree(source, staging, symlinks=False, ignore=ignore)
    except OSError:
        raise NativeRuntimeError("NATIVE_RELEASE_COPY_FAILED") from None
    for path in staging.rglob("*"):
        if path.is_symlink():
            raise NativeRuntimeError("NATIVE_RELEASE_SYMLINK_REJECTED")


def _disable_runtime_asset_recompile(release: Path) -> None:
    """Mantém public/assets imutável no runtime nativo com assets pré-compilados."""
    path = release / "config/environments/production.rb"
    try:
        if path.is_symlink() or not path.is_file():
            raise NativeRuntimeError("NATIVE_ASSET_POLICY_FILE_INVALID")
        raw = path.read_bytes()
    except OSError:
        raise NativeRuntimeError("NATIVE_ASSET_POLICY_FILE_INVALID") from None
    if raw.count(ASSET_AUTOCOMPILE_ON) != 1 or ASSET_AUTOCOMPILE_OFF in raw:
        raise NativeRuntimeError("NATIVE_ASSET_POLICY_MISMATCH")
    patched = raw.replace(ASSET_AUTOCOMPILE_ON, ASSET_AUTOCOMPILE_OFF)
    try:
        path.write_bytes(patched)
        if path.read_bytes() != patched:
            raise NativeRuntimeError("NATIVE_ASSET_POLICY_READBACK_FAILED")
    except OSError:
        raise NativeRuntimeError("NATIVE_ASSET_POLICY_WRITE_FAILED") from None


def _ensure_state(target_root: Path, source: Path, seed_sqlite: Path | None) -> Path:
    shared = target_root / "shared"
    shared.mkdir(mode=0o700, parents=True, exist_ok=True)
    for name in STATE_NAMES:
        (shared / name).mkdir(mode=0o700, exist_ok=True)

    files_src = source / "files"
    files_dst = shared / "files"
    if files_src.is_dir() and not any(files_dst.iterdir()):
        for child in files_src.iterdir():
            if child.is_symlink():
                raise NativeRuntimeError("NATIVE_STATE_SYMLINK_REJECTED")
            destination = files_dst / child.name
            if child.is_dir():
                shutil.copytree(child, destination, symlinks=False)
            elif child.is_file():
                shutil.copy2(child, destination)

    secret_src = source / "config/initializers/secret_token.rb"
    secret_dst = shared / "config/secret_token.rb"
    if secret_src.is_file() and not secret_dst.exists():
        shutil.copy2(secret_src, secret_dst)
        secret_dst.chmod(0o600)

    if seed_sqlite is not None:
        seed_sqlite = Path(seed_sqlite)
        db_dst = shared / "db/redmine.sqlite3"
        if not seed_sqlite.is_file() or seed_sqlite.is_symlink():
            raise NativeRuntimeError("NATIVE_SQLITE_SEED_INVALID")
        if not db_dst.exists():
            src = sqlite3.connect(f"file:{seed_sqlite}?mode=ro", uri=True)
            dst = sqlite3.connect(db_dst)
            try:
                src.backup(dst)
                if dst.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                    raise NativeRuntimeError("NATIVE_SQLITE_SEED_INTEGRITY_FAILED")
            finally:
                dst.close()
                src.close()
            db_dst.chmod(0o600)
    return shared


def _replace_with_state_link(release: Path, relative: str, destination: Path) -> None:
    path = release / relative
    if path.is_symlink():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    rel_target = os.path.relpath(destination, path.parent)
    path.symlink_to(rel_target, target_is_directory=destination.is_dir())


def _run(command: list[str], cwd: Path, env: dict[str, str], timeout: int = 360) -> None:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise NativeRuntimeError("NATIVE_COMMAND_FAILED") from None
    if result.returncode:
        raise NativeRuntimeError("NATIVE_COMMAND_FAILED")


def _install_bundle(release: Path) -> None:
    env = dict(os.environ)
    env.update({
        "BUNDLE_GEMFILE": str(release / "Gemfile"),
        "BUNDLE_PATH": str(release / "vendor/bundle"),
        "BUNDLE_DEPLOYMENT": "true",
        "BUNDLE_FROZEN": "true",
        "BUNDLE_WITHOUT": "development:test",
    })
    _run(["bundle", "config", "set", "--local", "path", "vendor/bundle"], release, env)
    _run(["bundle", "config", "set", "--local", "without", "development test"], release, env)
    _run(["bundle", "install", "--jobs", "4", "--retry", "2"], release, env)
    _run(["bundle", "check"], release, env, timeout=60)


def _metadata(release: Path, expected_sha: str, source_manifest: dict) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "repository": REPOSITORY,
        "source_sha": expected_sha,
        "source_release_manifest_sha256": _hash_file(release / RELEASE_MANIFEST),
        "application_tree_sha256": _tree_hash(release),
        "state_contract": {
            "database": "DATABASE_URL",
            "attachments": "shared/files",
            "secret_token": "shared/config/secret_token.rb",
            "tmp": "shared/tmp",
            "log": "shared/log",
            "assets": "precompiled_immutable",
        },
        "redmine_version": source_manifest.get("redmine_version"),
    }


def _verify_metadata(release: Path, expected_sha: str) -> dict:
    metadata = _read_json(release / NATIVE_METADATA)
    if (
        metadata.get("schema_version") != SCHEMA_VERSION
        or metadata.get("repository") != REPOSITORY
        or _sha(metadata.get("source_sha")) != _sha(expected_sha)
        or not re.fullmatch(r"[0-9a-f]{64}", str(metadata.get("application_tree_sha256", "")))
        or not re.fullmatch(r"[0-9a-f]{64}", str(metadata.get("source_release_manifest_sha256", "")))
    ):
        raise NativeRuntimeError("NATIVE_METADATA_INVALID")
    if _hash_file(release / RELEASE_MANIFEST) != metadata["source_release_manifest_sha256"]:
        raise NativeRuntimeError("NATIVE_METADATA_MANIFEST_MISMATCH")
    if _tree_hash(release) != metadata["application_tree_sha256"]:
        raise NativeRuntimeError("NATIVE_RELEASE_TREE_MISMATCH")
    verify_source_manifest(release, expected_sha)
    return metadata


def _set_current(target_root: Path, release: Path) -> None:
    current = target_root / "current"
    if current.exists() and not current.is_symlink():
        raise NativeRuntimeError("NATIVE_CURRENT_NOT_SYMLINK")
    temp = target_root / f".current.{os.getpid()}"
    try:
        if temp.exists() or temp.is_symlink():
            temp.unlink()
        temp.symlink_to(os.path.relpath(release, target_root), target_is_directory=True)
        os.replace(temp, current)
    finally:
        if temp.exists() or temp.is_symlink():
            temp.unlink()


def install_release(
    source: Path,
    target_root: Path,
    expected_sha: str,
    *,
    seed_sqlite: Path | None = None,
    install_bundle: bool = True,
) -> dict:
    source = _safe_root(source)
    target_root = _safe_root(target_root, must_exist=False)
    expected_sha = _sha(expected_sha)
    source_manifest = verify_source_manifest(source, expected_sha)
    if not install_bundle and os.environ.get("REQSYS_NATIVE_TEST_MODE") != "1":
        raise NativeRuntimeError("NATIVE_SKIP_BUNDLE_NOT_ALLOWED")

    target_root.mkdir(mode=0o755, parents=True, exist_ok=True)
    if target_root.is_symlink():
        raise NativeRuntimeError("NATIVE_ROOT_SYMLINK_REJECTED")
    releases = target_root / "releases"
    releases.mkdir(mode=0o755, exist_ok=True)
    shared = _ensure_state(target_root, source, seed_sqlite)
    release = releases / expected_sha

    if release.exists():
        if not release.is_dir() or release.is_symlink():
            raise NativeRuntimeError("NATIVE_RELEASE_COLLISION")
        metadata = _verify_metadata(release, expected_sha)
        _set_current(target_root, release)
        return metadata

    staging = releases / f".staging-{expected_sha}-{os.getpid()}"
    if staging.exists():
        raise NativeRuntimeError("NATIVE_STAGING_COLLISION")
    try:
        _copy_release(source, staging)
        _disable_runtime_asset_recompile(staging)
        _replace_with_state_link(staging, "files", shared / "files")
        _replace_with_state_link(staging, "tmp", shared / "tmp")
        _replace_with_state_link(staging, "log", shared / "log")
        secret = shared / "config/secret_token.rb"
        if secret.exists():
            _replace_with_state_link(staging, "config/initializers/secret_token.rb", secret)

        start = staging / "bin/reqsys-redmine-start"
        start.parent.mkdir(parents=True, exist_ok=True)
        start.write_text(START_SCRIPT, encoding="utf-8")
        start.chmod(0o755)

        if install_bundle:
            _install_bundle(staging)

        metadata = _metadata(staging, expected_sha, source_manifest)
        (staging / NATIVE_METADATA).write_bytes(_canonical_json(metadata))
        _verify_metadata(staging, expected_sha)
        staging.rename(release)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    _set_current(target_root, release)
    if _verify_metadata(release, expected_sha) != metadata:
        raise NativeRuntimeError("NATIVE_INSTALL_READBACK_FAILED")
    return metadata


def verify_install(target_root: Path, expected_sha: str) -> dict:
    target_root = _safe_root(target_root)
    current = target_root / "current"
    if not current.is_symlink():
        raise NativeRuntimeError("NATIVE_CURRENT_MISSING")
    try:
        release = current.resolve(strict=True)
    except OSError:
        raise NativeRuntimeError("NATIVE_CURRENT_INVALID") from None
    releases = (target_root / "releases").resolve()
    if release.parent != releases:
        raise NativeRuntimeError("NATIVE_CURRENT_OUTSIDE_RELEASES")
    if release.name != _sha(expected_sha):
        raise NativeRuntimeError("NATIVE_CURRENT_SHA_MISMATCH")
    return _verify_metadata(release, expected_sha)


def _backup_hashes(root: Path) -> dict[str, str]:
    result = {}
    for path in _relative_files(root, exclude=("manifest.json",)):
        result[path.relative_to(root).as_posix()] = _hash_file(path)
    return result


def verify_backup(backup_root: Path) -> dict:
    backup_root = _safe_root(backup_root)
    manifest = _read_json(backup_root / "manifest.json")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("database_adapter") != "sqlite3"
        or manifest.get("quiesced") is not True
        or manifest.get("contains_secrets") is not True
        or not isinstance(manifest.get("files_sha256"), dict)
    ):
        raise NativeRuntimeError("NATIVE_BACKUP_MANIFEST_INVALID")
    hashes = _backup_hashes(backup_root)
    if hashes != manifest["files_sha256"]:
        raise NativeRuntimeError("NATIVE_BACKUP_HASH_MISMATCH")
    db_path = backup_root / "db/redmine.sqlite3"
    try:
        db = sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", uri=True)
        try:
            if db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise NativeRuntimeError("NATIVE_BACKUP_SQLITE_INVALID")
        finally:
            db.close()
    except sqlite3.Error:
        raise NativeRuntimeError("NATIVE_BACKUP_SQLITE_INVALID") from None
    return manifest


def backup_sqlite(state_root: Path, output: Path, *, quiesced: bool) -> dict:
    state_root = _safe_root(state_root)
    output = Path(output)
    if not output.is_absolute() or output.exists() or output.is_symlink():
        raise NativeRuntimeError("NATIVE_BACKUP_OUTPUT_INVALID")
    if not quiesced:
        raise NativeRuntimeError("NATIVE_BACKUP_REQUIRES_QUIESCE")
    source_db = state_root / "db/redmine.sqlite3"
    if not source_db.is_file() or source_db.is_symlink():
        raise NativeRuntimeError("NATIVE_BACKUP_SQLITE_MISSING")

    staging = output.parent / f".{output.name}.staging-{os.getpid()}"
    if staging.exists():
        raise NativeRuntimeError("NATIVE_BACKUP_STAGING_COLLISION")
    try:
        (staging / "db").mkdir(parents=True, mode=0o700)
        for name in ("files", "config"):
            source = state_root / name
            target = staging / name
            if source.is_dir():
                shutil.copytree(source, target, symlinks=False)
            else:
                target.mkdir(mode=0o700)

        src = sqlite3.connect(f"file:{source_db}?mode=ro&immutable=1", uri=True)
        dst = sqlite3.connect(staging / "db/redmine.sqlite3")
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

        manifest = {
            "schema_version": 1,
            "database_adapter": "sqlite3",
            "quiesced": True,
            "contains_secrets": True,
            "files_sha256": _backup_hashes(staging),
        }
        (staging / "manifest.json").write_bytes(_canonical_json(manifest))
        verify_backup(staging)
        staging.rename(output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return verify_backup(output)


def restore_sqlite(backup_root: Path, target_state: Path) -> dict:
    backup_root = _safe_root(backup_root)
    target_state = Path(target_state)
    if not target_state.is_absolute() or target_state.exists() or target_state.is_symlink():
        raise NativeRuntimeError("NATIVE_RESTORE_TARGET_INVALID")
    manifest = verify_backup(backup_root)
    staging = target_state.parent / f".{target_state.name}.staging-{os.getpid()}"
    try:
        staging.mkdir(mode=0o700)
        for name in ("db", "files", "config"):
            shutil.copytree(backup_root / name, staging / name, symlinks=False)
        for name in ("tmp", "log", "backups"):
            (staging / name).mkdir(mode=0o700)
        db_path = staging / "db/redmine.sqlite3"
        db = sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", uri=True)
        try:
            if db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise NativeRuntimeError("NATIVE_RESTORE_SQLITE_INVALID")
        finally:
            db.close()
        staging.rename(target_state)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)

    install = sub.add_parser("install")
    install.add_argument("--source", required=True)
    install.add_argument("--target-root", required=True)
    install.add_argument("--expected-sha", required=True)
    install.add_argument("--seed-sqlite-db")
    install.add_argument("--skip-bundle", action="store_true")

    verify = sub.add_parser("verify")
    verify.add_argument("--target-root", required=True)
    verify.add_argument("--expected-sha", required=True)

    backup = sub.add_parser("backup-sqlite")
    backup.add_argument("--state-root", required=True)
    backup.add_argument("--output", required=True)
    backup.add_argument("--quiesced", action="store_true")

    check_backup = sub.add_parser("verify-backup")
    check_backup.add_argument("--backup-root", required=True)

    restore = sub.add_parser("restore-sqlite")
    restore.add_argument("--backup-root", required=True)
    restore.add_argument("--target-state", required=True)

    args = parser.parse_args(argv)
    try:
        if args.action == "install":
            payload = install_release(
                Path(args.source),
                Path(args.target_root),
                args.expected_sha,
                seed_sqlite=Path(args.seed_sqlite_db) if args.seed_sqlite_db else None,
                install_bundle=not args.skip_bundle,
            )
        elif args.action == "verify":
            payload = verify_install(Path(args.target_root), args.expected_sha)
        elif args.action == "backup-sqlite":
            payload = backup_sqlite(Path(args.state_root), Path(args.output), quiesced=args.quiesced)
        elif args.action == "verify-backup":
            payload = verify_backup(Path(args.backup_root))
        else:
            payload = restore_sqlite(Path(args.backup_root), Path(args.target_state))
    except NativeRuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
