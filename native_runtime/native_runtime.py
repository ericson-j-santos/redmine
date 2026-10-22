#!/usr/bin/env python3
"""Runtime Linux nativo e portátil para o Redmine ReqSys.

Não provisiona host, não publica ambiente e não manipula secrets remotos.
Instala releases imutáveis, separa estado persistente e produz backup/restore
verificável para SQLite e PostgreSQL. Credenciais PostgreSQL são aceitas somente
por ambiente e nunca são incluídas nos argumentos dos subprocessos ou recibos.
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
import stat
import subprocess
import sys
import tempfile
from typing import Iterable
from urllib.parse import parse_qsl, unquote, urlsplit

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
POSTGRES_ARCHIVE = Path("db/redmine.pgdump")
POSTGRES_RESTORE_RECEIPT = Path(".reqsys-postgresql-restore.json")
POSTGRES_BACKUP_SCHEMA_VERSION = 2
POSTGRES_MINIMUM_MAJOR = 16
POSTGRES_COMPONENTS = {"attachments": "files", "configuration": "config"}
POSTGRES_READBACK_SQL = """
SELECT json_build_object(
  'schema_migrations_count', (SELECT count(*) FROM public.schema_migrations),
  'schema_migrations_max', COALESCE((SELECT max(version) FROM public.schema_migrations), ''),
  'projects_count', (SELECT count(*) FROM public.projects),
  'projects_max_id', COALESCE((SELECT max(id) FROM public.projects), 0),
  'issues_count', (SELECT count(*) FROM public.issues),
  'issues_max_id', COALESCE((SELECT max(id) FROM public.issues), 0),
  'attachments_count', (SELECT count(*) FROM public.attachments),
  'attachments_max_id', COALESCE((SELECT max(id) FROM public.attachments), 0),
  'users_count', (SELECT count(*) FROM public.users),
  'users_max_id', COALESCE((SELECT max(id) FROM public.users), 0)
)::text;
""".strip()
POSTGRES_USER_OBJECT_COUNT_SQL = """
SELECT (
  SELECT count(*)
  FROM pg_catalog.pg_class AS object
  JOIN pg_catalog.pg_namespace AS namespace ON namespace.oid = object.relnamespace
  WHERE namespace.nspname NOT IN ('pg_catalog', 'information_schema')
    AND namespace.nspname !~ '^pg_toast'
    AND object.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
) + (
  SELECT count(*)
  FROM pg_catalog.pg_namespace
  WHERE nspname NOT IN ('pg_catalog', 'information_schema', 'public')
    AND nspname !~ '^pg_toast'
) + (
  SELECT count(*)
  FROM pg_catalog.pg_proc AS object
  JOIN pg_catalog.pg_namespace AS namespace ON namespace.oid = object.pronamespace
  WHERE namespace.nspname NOT IN ('pg_catalog', 'information_schema')
    AND namespace.nspname !~ '^pg_toast'
) + (
  SELECT count(*)
  FROM pg_catalog.pg_type AS object
  JOIN pg_catalog.pg_namespace AS namespace ON namespace.oid = object.typnamespace
  WHERE namespace.nspname NOT IN ('pg_catalog', 'information_schema')
    AND namespace.nspname !~ '^pg_toast'
) + (
  SELECT count(*) FROM pg_catalog.pg_extension WHERE extname <> 'plpgsql'
) + (
  SELECT count(*) FROM pg_catalog.pg_event_trigger
) + (
  SELECT count(*) FROM pg_catalog.pg_foreign_data_wrapper
) + (
  SELECT count(*) FROM pg_catalog.pg_foreign_server
) + (
  SELECT count(*) FROM pg_catalog.pg_publication
);
""".strip()
POSTGRES_DATABASE_SETTINGS_SQL = """
WITH database AS (
  SELECT source.*, pg_catalog.to_jsonb(source) AS payload
  FROM pg_catalog.pg_database AS source
  WHERE datname = pg_catalog.current_database()
)
SELECT json_build_object(
  'encoding', pg_catalog.pg_encoding_to_char(encoding),
  'lc_collate', datcollate,
  'lc_ctype', datctype,
  'locale_provider', COALESCE(payload ->> 'datlocprovider', 'c'),
  'icu_locale', COALESCE(payload ->> 'daticulocale', payload ->> 'datlocale', ''),
  'icu_rules', COALESCE(payload ->> 'daticurules', ''),
  'collation_version', COALESCE(payload ->> 'datcollversion', '')
)::text
FROM database;
""".strip()
POSTGRES_NONDUMPABLE_COUNT_SQL = """
SELECT (
  SELECT count(*) FROM pg_catalog.pg_largeobject_metadata
) + (
  SELECT count(*)
  FROM pg_catalog.pg_subscription
  WHERE subdbid = (SELECT oid FROM pg_catalog.pg_database WHERE datname = pg_catalog.current_database())
) + (
  SELECT count(*)
  FROM pg_catalog.pg_db_role_setting
  WHERE setdatabase = (SELECT oid FROM pg_catalog.pg_database WHERE datname = pg_catalog.current_database())
     OR (
       setdatabase = 0
       AND setrole = (SELECT oid FROM pg_catalog.pg_roles WHERE rolname = CURRENT_USER)
     )
) + (
  SELECT count(*)
  FROM pg_catalog.pg_prepared_xacts
  WHERE database = pg_catalog.current_database()
) + (
  SELECT count(*)
  FROM pg_catalog.pg_replication_slots
  WHERE database = pg_catalog.current_database()
) + (
  SELECT CASE WHEN datacl IS NULL THEN 0 ELSE 1 END
       + CASE WHEN datdba = (SELECT oid FROM pg_catalog.pg_roles WHERE rolname = CURRENT_USER)
              THEN 0 ELSE 1 END
  FROM pg_catalog.pg_database
  WHERE datname = pg_catalog.current_database()
) + (
  SELECT count(*)
  FROM pg_catalog.pg_stat_activity
  WHERE datid = (SELECT oid FROM pg_catalog.pg_database WHERE datname = pg_catalog.current_database())
    AND pid <> pg_catalog.pg_backend_pid()
    AND backend_type = 'client backend'
);
""".strip()
POSTGRES_ROLE_PROFILE_SQL = """
SELECT json_build_object(
  'superuser', role.rolsuper,
  'create_role', role.rolcreaterole,
  'create_database', role.rolcreatedb,
  'replication', role.rolreplication,
  'bypass_rls', role.rolbypassrls,
  'login', role.rolcanlogin,
  'owns_database', database.datdba = role.oid,
  'effective_memberships', (
    SELECT count(*)
    FROM pg_catalog.pg_roles AS candidate
    WHERE candidate.oid <> role.oid
      AND candidate.rolname <> 'pg_database_owner'
      AND pg_catalog.pg_has_role(role.oid, candidate.oid, 'MEMBER')
  )
)::text
FROM pg_catalog.pg_roles AS role
JOIN pg_catalog.pg_database AS database
  ON database.datname = pg_catalog.current_database()
WHERE role.rolname = CURRENT_USER;
""".strip()

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


def _read_json_with_sha256(path: Path) -> tuple[dict, str]:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    except OSError:
        raise NativeRuntimeError("NATIVE_JSON_UNAVAILABLE") from None
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise NativeRuntimeError("NATIVE_JSON_UNAVAILABLE")
        chunks: list[bytes] = []
        total = 0
        while total <= MAX_JSON_BYTES:
            chunk = os.read(descriptor, min(64 * 1024, MAX_JSON_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
        if total > MAX_JSON_BYTES:
            raise NativeRuntimeError("NATIVE_JSON_TOO_LARGE")
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
        if _stat_identity(before, include_content=True) != _stat_identity(
            after, include_content=True
        ):
            raise NativeRuntimeError("NATIVE_JSON_CHANGED_DURING_READ")
    except OSError:
        raise NativeRuntimeError("NATIVE_JSON_UNAVAILABLE") from None
    finally:
        os.close(descriptor)

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
    return data, hashlib.sha256(raw).hexdigest()


def _read_json(path: Path) -> dict:
    return _read_json_with_sha256(path)[0]


def _canonical_json(data: object) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _hash_file(path: Path) -> str:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    except FileNotFoundError:
        raise NativeRuntimeError("NATIVE_FILE_INVALID") from None
    except OSError:
        raise NativeRuntimeError("NATIVE_FILE_UNAVAILABLE") from None
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise NativeRuntimeError("NATIVE_FILE_INVALID")
        digest = hashlib.sha256()
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        after = os.fstat(descriptor)
        if _stat_identity(before, include_content=True) != _stat_identity(after, include_content=True):
            raise NativeRuntimeError("NATIVE_FILE_CHANGED_DURING_READ")
        return digest.hexdigest()
    except OSError:
        raise NativeRuntimeError("NATIVE_FILE_UNAVAILABLE") from None
    finally:
        os.close(descriptor)


def _stat_identity(value: os.stat_result, *, include_content: bool = False) -> tuple[int, ...]:
    identity = (value.st_dev, value.st_ino, stat.S_IFMT(value.st_mode))
    if include_content:
        identity += (value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    return identity


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


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


def _run_capture(command: list[str], cwd: Path, env: dict[str, str], timeout: int = 60) -> str:
    """Executa um comando sem propagar argumentos, ambiente ou saída no erro."""
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
    if result.returncode or len(result.stdout.encode("utf-8", errors="replace")) > MAX_JSON_BYTES:
        raise NativeRuntimeError("NATIVE_COMMAND_FAILED")
    return result.stdout.strip()


def _minimal_subprocess_environment() -> dict[str, str]:
    inherited = ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ")
    return {name: os.environ[name] for name in inherited if name in os.environ}


def _postgres_connection(database_url: str) -> tuple[dict[str, str], str]:
    """Valida uma URI libpq e devolve ambiente + identidade sem credencial."""
    if (
        not isinstance(database_url, str)
        or not database_url
        or len(database_url) > 4096
        or any(character in database_url for character in ("\x00", "\n", "\r"))
    ):
        raise NativeRuntimeError("NATIVE_POSTGRES_URL_INVALID")
    try:
        parsed = urlsplit(database_url)
        host = parsed.hostname
        port = parsed.port or 5432
    except ValueError:
        raise NativeRuntimeError("NATIVE_POSTGRES_URL_INVALID") from None
    database = unquote(parsed.path[1:]) if parsed.path.startswith("/") else ""
    username = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    if (
        parsed.scheme not in ("postgres", "postgresql")
        or not host
        or not database
        or "/" in database
        or parsed.fragment
        or not (1 <= port <= 65535)
        or any(
            character in value
            for value in (host, database, username, password)
            for character in ("\x00", "\n", "\r")
        )
    ):
        raise NativeRuntimeError("NATIVE_POSTGRES_URL_INVALID")
    identity = {
        "database": database,
        "host": host.lower(),
        "port": port,
        "username": username,
    }
    identity_sha256 = hashlib.sha256(_canonical_json(identity)).hexdigest()
    # Não repassa o ambiente da aplicação (inclusive URLs/segredos) aos
    # clientes PostgreSQL. Só PATH/locale/fuso são necessários para executar
    # os binários de forma determinística; toda configuração libpq aceita é
    # preenchida abaixo a partir da URL já validada.
    env = _minimal_subprocess_environment()
    env.update({
        "PGHOST": host,
        "PGPORT": str(port),
        "PGDATABASE": database,
        "PGAPPNAME": "reqsys-native-backup",
        "PGCONNECT_TIMEOUT": "10",
        "PGPASSFILE": os.devnull,
    })
    if username:
        env["PGUSER"] = username
    if password:
        env["PGPASSWORD"] = password
    query_environment = {
        "sslmode": "PGSSLMODE",
        "sslcert": "PGSSLCERT",
        "sslkey": "PGSSLKEY",
        "sslrootcert": "PGSSLROOTCERT",
        "connect_timeout": "PGCONNECT_TIMEOUT",
    }
    try:
        query = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        raise NativeRuntimeError("NATIVE_POSTGRES_URL_INVALID") from None
    if len({name for name, _ in query}) != len(query):
        raise NativeRuntimeError("NATIVE_POSTGRES_URL_INVALID")
    for name, value in query:
        target = query_environment.get(name)
        if (
            target is None
            or not value
            or len(value) > 4096
            or any(character in value for character in ("\x00", "\n", "\r"))
        ):
            raise NativeRuntimeError("NATIVE_POSTGRES_URL_INVALID")
        if name == "sslmode" and value not in {
            "disable", "allow", "prefer", "require", "verify-ca", "verify-full",
        }:
            raise NativeRuntimeError("NATIVE_POSTGRES_URL_INVALID")
        if name == "connect_timeout" and (
            not re.fullmatch(r"\d{1,3}", value) or not (1 <= int(value) <= 120)
        ):
            raise NativeRuntimeError("NATIVE_POSTGRES_URL_INVALID")
        env[target] = value
    return env, identity_sha256


def _postgres_tool_version(binary: str) -> dict[str, int | str]:
    output = _run_capture(
        [binary, "--version"],
        Path.cwd(),
        _minimal_subprocess_environment(),
        timeout=15,
    )
    match = re.search(r"\b(\d+)(?:\.(\d+))?\b", output)
    if not match:
        raise NativeRuntimeError("NATIVE_POSTGRES_TOOL_VERSION_INVALID")
    return {"version": match.group(0), "major": int(match.group(1))}


def _postgres_query(database_url: str, sql: str, *, timeout: int = 60) -> str:
    env, _ = _postgres_connection(database_url)
    return _run_capture(
        [
            "psql", "--no-password", "--no-psqlrc", "--tuples-only", "--no-align", "--quiet",
            "--set", "ON_ERROR_STOP=1", "--command", sql,
        ],
        Path.cwd(),
        env,
        timeout=timeout,
    )


def _run_postgres_sql(database_url: str, sql: str) -> None:
    _postgres_query(database_url, sql, timeout=120)


def _postgres_server_version(database_url: str) -> dict[str, int]:
    raw = _postgres_query(database_url, "SHOW server_version_num;")
    if not re.fullmatch(r"\d{5,6}", raw):
        raise NativeRuntimeError("NATIVE_POSTGRES_SERVER_VERSION_INVALID")
    version_num = int(raw)
    major = version_num // 10000
    if major < POSTGRES_MINIMUM_MAJOR:
        raise NativeRuntimeError("NATIVE_POSTGRES_SERVER_VERSION_UNSUPPORTED")
    return {"version_num": version_num, "major": major}


def _validate_postgres_database_settings(payload: object) -> dict[str, str]:
    required = {
        "encoding", "lc_collate", "lc_ctype", "locale_provider",
        "icu_locale", "icu_rules", "collation_version",
    }
    if (
        not isinstance(payload, dict)
        or set(payload) != required
        or not re.fullmatch(r"[A-Z0-9_-]{1,32}", str(payload.get("encoding", "")))
        or not re.fullmatch(r"[a-z]{1,16}", str(payload.get("locale_provider", "")))
        or any(
            not isinstance(payload.get(name), str)
            or not payload[name]
            or len(payload[name]) > 255
            or any(character in payload[name] for character in ("\x00", "\n", "\r"))
            for name in ("lc_collate", "lc_ctype")
        )
        or any(
            not isinstance(payload.get(name), str)
            or len(payload[name]) > 1024
            or any(character in payload[name] for character in ("\x00", "\n", "\r"))
            for name in ("icu_locale", "icu_rules", "collation_version")
        )
    ):
        raise NativeRuntimeError("NATIVE_POSTGRES_DATABASE_SETTINGS_INVALID")
    return payload


def _postgres_database_settings(database_url: str) -> dict[str, str]:
    raw = _postgres_query(database_url, POSTGRES_DATABASE_SETTINGS_SQL)
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError):
        raise NativeRuntimeError("NATIVE_POSTGRES_DATABASE_SETTINGS_INVALID") from None
    return _validate_postgres_database_settings(payload)


def _validate_postgres_role_profile(payload: object) -> dict[str, bool | int]:
    expected = {
        "superuser": False,
        "create_role": False,
        "create_database": False,
        "replication": False,
        "bypass_rls": False,
        "login": True,
        "owns_database": True,
        "effective_memberships": 0,
    }
    boolean_keys = set(expected) - {"effective_memberships"}
    if (
        not isinstance(payload, dict)
        or payload != expected
        or any(type(payload.get(name)) is not bool for name in boolean_keys)
        or type(payload.get("effective_memberships")) is not int
    ):
        raise NativeRuntimeError("NATIVE_POSTGRES_ROLE_PROFILE_INVALID")
    return payload


def _postgres_role_profile(database_url: str) -> dict[str, bool | int]:
    raw = _postgres_query(database_url, POSTGRES_ROLE_PROFILE_SQL)
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError):
        raise NativeRuntimeError("NATIVE_POSTGRES_ROLE_PROFILE_INVALID") from None
    return _validate_postgres_role_profile(payload)


def _validate_postgres_readback(payload: object) -> dict[str, int | str]:
    integer_keys = {
        "schema_migrations_count", "projects_count", "projects_max_id",
        "issues_count", "issues_max_id", "attachments_count",
        "attachments_max_id", "users_count", "users_max_id",
    }
    expected = integer_keys | {"schema_migrations_max"}
    if (
        not isinstance(payload, dict)
        or set(payload) != expected
        or any(type(payload.get(key)) is not int or payload[key] < 0 for key in integer_keys)
        or not isinstance(payload.get("schema_migrations_max"), str)
    ):
        raise NativeRuntimeError("NATIVE_POSTGRES_READBACK_INVALID")
    return payload


def _postgres_readback(database_url: str) -> dict[str, int | str]:
    raw = _postgres_query(database_url, POSTGRES_READBACK_SQL)
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError):
        raise NativeRuntimeError("NATIVE_POSTGRES_READBACK_INVALID") from None
    return _validate_postgres_readback(payload)


def _postgres_user_object_count(database_url: str) -> int:
    raw = _postgres_query(database_url, POSTGRES_USER_OBJECT_COUNT_SQL)
    if not re.fullmatch(r"\d+", raw):
        raise NativeRuntimeError("NATIVE_POSTGRES_EMPTY_CHECK_INVALID")
    return int(raw)


def _postgres_nondumpable_count(database_url: str) -> int:
    raw = _postgres_query(database_url, POSTGRES_NONDUMPABLE_COUNT_SQL)
    if not re.fullmatch(r"\d+", raw):
        raise NativeRuntimeError("NATIVE_POSTGRES_EMPTY_CHECK_INVALID")
    return int(raw)


def _postgres_schema_toc_entries(database_url: str, working_directory: Path) -> list[str]:
    working_directory = _safe_root(working_directory)
    pg_env, _ = _postgres_connection(database_url)
    try:
        with tempfile.TemporaryDirectory(
            prefix=".reqsys-postgresql-empty-",
            dir=working_directory,
        ) as temporary:
            temporary_root = Path(temporary)
            archive = temporary_root / "schema.pgdump"
            _run(
                [
                    "pg_dump", "--schema-only", "--format=custom", "--no-password",
                    "--no-tablespaces", "--file", str(archive),
                ],
                temporary_root,
                pg_env,
                timeout=300,
            )
            if not archive.is_file() or archive.is_symlink() or archive.stat().st_size == 0:
                raise NativeRuntimeError("NATIVE_POSTGRES_EMPTY_CHECK_INVALID")
            listing = _run_capture(
                ["pg_restore", "--list", str(archive)],
                temporary_root,
                _minimal_subprocess_environment(),
                timeout=120,
            )
    except NativeRuntimeError:
        raise
    except OSError:
        raise NativeRuntimeError("NATIVE_POSTGRES_EMPTY_CHECK_INVALID") from None
    return [
        line.strip()
        for line in listing.splitlines()
        if line.strip() and not line.lstrip().startswith(";")
    ]


def _require_postgres_pristine_target(database_url: str, working_directory: Path) -> None:
    # O dump de schema é a etapa potencialmente longa; a consulta de objetos
    # não dumpáveis e sessões concorrentes fica por último para reduzir a
    # janela entre a prova de quiescência e o pg_restore.
    if (
        _postgres_schema_toc_entries(database_url, working_directory)
        or _postgres_nondumpable_count(database_url) != 0
    ):
        raise NativeRuntimeError("NATIVE_POSTGRES_RESTORE_TARGET_NOT_EMPTY")


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


def _directory_names(descriptor: int, error_code: str) -> list[str]:
    try:
        return sorted(os.listdir(descriptor))
    except OSError:
        raise NativeRuntimeError(error_code) from None


def _entry_stat(directory: int, name: str, error_code: str) -> os.stat_result:
    try:
        return os.stat(name, dir_fd=directory, follow_symlinks=False)
    except OSError:
        raise NativeRuntimeError(error_code) from None


def _open_verified_entry(
    directory: int,
    name: str,
    expected: os.stat_result,
    *,
    is_directory: bool,
    error_code: str,
) -> int:
    flags = os.O_RDONLY | os.O_NOFOLLOW
    flags |= os.O_DIRECTORY if is_directory else os.O_NONBLOCK
    try:
        descriptor = os.open(name, flags, dir_fd=directory)
    except OSError:
        raise NativeRuntimeError(error_code) from None
    try:
        actual = os.fstat(descriptor)
        expected_type = stat.S_ISDIR if is_directory else stat.S_ISREG
        if (
            not expected_type(actual.st_mode)
            or _stat_identity(expected) != _stat_identity(actual)
        ):
            raise NativeRuntimeError(error_code)
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _hash_open_regular(descriptor: int, error_code: str) -> str:
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise NativeRuntimeError(error_code)
        digest = hashlib.sha256()
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        after = os.fstat(descriptor)
    except OSError:
        raise NativeRuntimeError(error_code) from None
    if _stat_identity(before, include_content=True) != _stat_identity(after, include_content=True):
        raise NativeRuntimeError(error_code)
    return digest.hexdigest()


def _hash_backup_directory(
    directory: int,
    prefix: Path,
    result: dict[str, str],
) -> None:
    for name in _directory_names(directory, "NATIVE_BACKUP_TREE_INVALID"):
        before = _entry_stat(directory, name, "NATIVE_BACKUP_TREE_INVALID")
        relative = prefix / name
        if stat.S_ISDIR(before.st_mode):
            child = _open_verified_entry(
                directory,
                name,
                before,
                is_directory=True,
                error_code="NATIVE_BACKUP_TREE_INVALID",
            )
            try:
                _hash_backup_directory(child, relative, result)
            finally:
                os.close(child)
        elif stat.S_ISREG(before.st_mode):
            child = _open_verified_entry(
                directory,
                name,
                before,
                is_directory=False,
                error_code="NATIVE_BACKUP_TREE_INVALID",
            )
            try:
                # O manifesto também é aberto/validado como regular, mas não
                # participa do mapa que ele próprio contém.
                if relative.as_posix() != "manifest.json":
                    result[relative.as_posix()] = _hash_open_regular(
                        child, "NATIVE_BACKUP_TREE_INVALID"
                    )
            finally:
                os.close(child)
        else:
            raise NativeRuntimeError("NATIVE_BACKUP_NODE_INVALID")


def _backup_hashes(root: Path) -> dict[str, str]:
    try:
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError:
        raise NativeRuntimeError("NATIVE_BACKUP_TREE_INVALID") from None
    try:
        result: dict[str, str] = {}
        _hash_backup_directory(descriptor, Path(), result)
        return result
    finally:
        os.close(descriptor)


def _copy_open_regular(source: int, target: int) -> None:
    try:
        before = os.fstat(source)
        if not stat.S_ISREG(before.st_mode):
            raise NativeRuntimeError("NATIVE_STATE_NODE_INVALID")
        while True:
            chunk = os.read(source, 1024 * 1024)
            if not chunk:
                break
            view = memoryview(chunk)
            while view:
                written = os.write(target, view)
                if written <= 0:
                    raise NativeRuntimeError("NATIVE_STATE_COPY_FAILED")
                view = view[written:]
        after = os.fstat(source)
    except OSError:
        raise NativeRuntimeError("NATIVE_STATE_COPY_FAILED") from None
    if _stat_identity(before, include_content=True) != _stat_identity(after, include_content=True):
        raise NativeRuntimeError("NATIVE_STATE_CHANGED_DURING_COPY")


def _copy_backup_directory(source: int, target: int) -> None:
    for name in _directory_names(source, "NATIVE_STATE_COPY_FAILED"):
        before = _entry_stat(source, name, "NATIVE_STATE_COPY_FAILED")
        if stat.S_ISDIR(before.st_mode):
            source_child = _open_verified_entry(
                source,
                name,
                before,
                is_directory=True,
                error_code="NATIVE_STATE_NODE_INVALID",
            )
            target_child = -1
            try:
                os.mkdir(name, mode=0o700, dir_fd=target)
                target_child = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=target,
                )
                _copy_backup_directory(source_child, target_child)
            except NativeRuntimeError:
                raise
            except OSError:
                raise NativeRuntimeError("NATIVE_STATE_COPY_FAILED") from None
            finally:
                os.close(source_child)
                if target_child >= 0:
                    os.close(target_child)
        elif stat.S_ISREG(before.st_mode):
            source_child = _open_verified_entry(
                source,
                name,
                before,
                is_directory=False,
                error_code="NATIVE_STATE_NODE_INVALID",
            )
            target_child = -1
            try:
                target_child = os.open(
                    name,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=target,
                )
                _copy_open_regular(source_child, target_child)
            except NativeRuntimeError:
                raise
            except OSError:
                raise NativeRuntimeError("NATIVE_STATE_COPY_FAILED") from None
            finally:
                os.close(source_child)
                if target_child >= 0:
                    os.close(target_child)
        else:
            raise NativeRuntimeError("NATIVE_STATE_NODE_INVALID")


def _copy_backup_component(source: Path, target: Path, *, allow_missing: bool = False) -> None:
    try:
        source_descriptor = os.open(
            source,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
    except FileNotFoundError:
        if not allow_missing:
            raise NativeRuntimeError("NATIVE_STATE_COMPONENT_MISSING") from None
        try:
            target.mkdir(mode=0o700)
        except OSError:
            raise NativeRuntimeError("NATIVE_STATE_COPY_FAILED") from None
        return
    except OSError:
        raise NativeRuntimeError("NATIVE_STATE_COMPONENT_INVALID") from None
    target_descriptor = -1
    try:
        if not stat.S_ISDIR(os.fstat(source_descriptor).st_mode):
            raise NativeRuntimeError("NATIVE_STATE_COMPONENT_INVALID")
        target.mkdir(mode=0o700)
        target_descriptor = os.open(
            target,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
        _copy_backup_directory(source_descriptor, target_descriptor)
    except NativeRuntimeError:
        raise
    except OSError:
        raise NativeRuntimeError("NATIVE_STATE_COPY_FAILED") from None
    finally:
        os.close(source_descriptor)
        if target_descriptor >= 0:
            os.close(target_descriptor)


def _harden_backup_tree(root: Path) -> None:
    try:
        root.chmod(0o700)
    except OSError:
        raise NativeRuntimeError("NATIVE_BACKUP_PERMISSION_FAILED") from None
    for path in sorted(root.rglob("*"), key=lambda value: value.as_posix()):
        if path.is_symlink():
            raise NativeRuntimeError("NATIVE_BACKUP_SYMLINK_REJECTED")
        try:
            if path.is_dir():
                path.chmod(0o700)
            elif path.is_file():
                path.chmod(0o600)
            else:
                raise NativeRuntimeError("NATIVE_BACKUP_NODE_INVALID")
        except OSError:
            raise NativeRuntimeError("NATIVE_BACKUP_PERMISSION_FAILED") from None


def _verify_sqlite_backup(backup_root: Path, manifest: dict) -> dict:
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


def _verify_postgresql_backup(backup_root: Path, manifest: dict, expected_sha: str | None) -> dict:
    if expected_sha is None:
        raise NativeRuntimeError("NATIVE_BACKUP_EXPECTED_SHA_REQUIRED")
    expected_sha = _sha(expected_sha)
    source_identity = manifest.get("source_identity")
    database = manifest.get("database")
    hashes = manifest.get("files_sha256")
    if (
        set(manifest) != {
            "schema_version", "database_adapter", "quiesced", "contains_secrets",
            "source_identity", "database", "components", "application_readback",
            "files_sha256",
        }
        or manifest.get("schema_version") != POSTGRES_BACKUP_SCHEMA_VERSION
        or manifest.get("database_adapter") != "postgresql"
        or manifest.get("quiesced") is not True
        or manifest.get("contains_secrets") is not True
        or manifest.get("components") != POSTGRES_COMPONENTS
        or not isinstance(source_identity, dict)
        or set(source_identity) != {
            "repository", "source_sha", "source_release_manifest_sha256",
            "application_tree_sha256",
        }
        or source_identity.get("repository") != REPOSITORY
        or _sha(source_identity.get("source_sha")) != expected_sha
        or not re.fullmatch(r"[0-9a-f]{64}", str(source_identity.get("source_release_manifest_sha256", "")))
        or not re.fullmatch(r"[0-9a-f]{64}", str(source_identity.get("application_tree_sha256", "")))
        or not isinstance(database, dict)
        or set(database) != {
            "archive", "format", "server_version_num", "server_major",
            "pg_dump_version", "pg_dump_major", "source_identity_sha256",
            "database_settings", "role_profile",
        }
        or database.get("archive") != POSTGRES_ARCHIVE.as_posix()
        or database.get("format") != "custom"
        or type(database.get("server_version_num")) is not int
        or type(database.get("server_major")) is not int
        or database["server_version_num"] // 10000 != database["server_major"]
        or database["server_major"] < POSTGRES_MINIMUM_MAJOR
        or not isinstance(database.get("pg_dump_version"), str)
        or not re.fullmatch(r"\d+(?:\.\d+){0,2}", database.get("pg_dump_version", ""))
        or type(database.get("pg_dump_major")) is not int
        or database["pg_dump_major"] != database["server_major"]
        or int(database["pg_dump_version"].split(".", 1)[0]) != database["pg_dump_major"]
        or not re.fullmatch(r"[0-9a-f]{64}", str(database.get("source_identity_sha256", "")))
        or not isinstance(database.get("database_settings"), dict)
        or not isinstance(database.get("role_profile"), dict)
        or not isinstance(hashes, dict)
        or not hashes
        or any(
            not isinstance(path, str)
            or not re.fullmatch(r"[0-9a-f]{64}", str(digest))
            for path, digest in hashes.items()
        )
    ):
        raise NativeRuntimeError("NATIVE_BACKUP_MANIFEST_INVALID")
    _validate_postgres_database_settings(database["database_settings"])
    _validate_postgres_role_profile(database["role_profile"])
    _validate_postgres_readback(manifest.get("application_readback"))
    actual_hashes = _backup_hashes(backup_root)
    if actual_hashes != hashes:
        raise NativeRuntimeError("NATIVE_BACKUP_HASH_MISMATCH")
    required = {POSTGRES_ARCHIVE.as_posix()}
    if (
        not required <= set(hashes)
        or not (backup_root / "files").is_dir()
        or not (backup_root / "config").is_dir()
    ):
        raise NativeRuntimeError("NATIVE_BACKUP_COMPONENT_MISSING")
    restore_version = _postgres_tool_version("pg_restore")
    if restore_version["major"] != database["pg_dump_major"]:
        raise NativeRuntimeError("NATIVE_POSTGRES_TOOL_VERSION_MISMATCH")
    archive = backup_root / POSTGRES_ARCHIVE
    listing = _run_capture(
        ["pg_restore", "--list", str(archive)],
        backup_root,
        _minimal_subprocess_environment(),
        timeout=120,
    )
    if not listing:
        raise NativeRuntimeError("NATIVE_POSTGRES_ARCHIVE_INVALID")
    return manifest


def _verify_backup_manifest(
    backup_root: Path,
    manifest: dict,
    expected_sha: str | None,
) -> dict:
    adapter = manifest.get("database_adapter")
    if adapter == "sqlite3":
        return _verify_sqlite_backup(backup_root, manifest)
    if adapter == "postgresql":
        return _verify_postgresql_backup(backup_root, manifest, expected_sha)
    raise NativeRuntimeError("NATIVE_BACKUP_MANIFEST_INVALID")


def verify_backup(backup_root: Path, expected_sha: str | None = None) -> dict:
    backup_root = _safe_root(backup_root)
    manifest = _read_json(backup_root / "manifest.json")
    return _verify_backup_manifest(backup_root, manifest, expected_sha)


def backup_sqlite(state_root: Path, output: Path, *, quiesced: bool) -> dict:
    state_root = _safe_root(state_root)
    output = Path(output)
    if not output.is_absolute() or output.exists() or output.is_symlink():
        raise NativeRuntimeError("NATIVE_BACKUP_OUTPUT_INVALID")
    _safe_root(output.parent)
    staging = output.parent / f".{output.name}.staging-{os.getpid()}"
    if any(
        _is_within(candidate, state_root / component)
        for candidate in (output, staging)
        for component in ("files", "config")
    ):
        raise NativeRuntimeError("NATIVE_BACKUP_OUTPUT_RECURSIVE")
    if not quiesced:
        raise NativeRuntimeError("NATIVE_BACKUP_REQUIRES_QUIESCE")
    source_db = state_root / "db/redmine.sqlite3"
    if not source_db.is_file() or source_db.is_symlink():
        raise NativeRuntimeError("NATIVE_BACKUP_SQLITE_MISSING")

    if staging.exists() or staging.is_symlink():
        raise NativeRuntimeError("NATIVE_BACKUP_STAGING_COLLISION")
    staging_created = False
    try:
        staging.mkdir(mode=0o700)
        staging_created = True
        (staging / "db").mkdir(mode=0o700)
        for name in ("files", "config"):
            _copy_backup_component(state_root / name, staging / name, allow_missing=True)

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
        _harden_backup_tree(staging)
        (staging / "manifest.json").write_bytes(_canonical_json(manifest))
        (staging / "manifest.json").chmod(0o600)
        verify_backup(staging)
        staging.rename(output)
    except Exception:
        if staging_created:
            shutil.rmtree(staging, ignore_errors=True)
        raise
    return verify_backup(output)


def backup_postgresql(
    target_root: Path,
    output: Path,
    expected_sha: str,
    database_url: str,
    *,
    quiesced: bool,
) -> dict:
    target_root = _safe_root(target_root)
    output = Path(output)
    expected_sha = _sha(expected_sha)
    if not output.is_absolute() or output.exists() or output.is_symlink():
        raise NativeRuntimeError("NATIVE_BACKUP_OUTPUT_INVALID")
    _safe_root(output.parent)
    staging = output.parent / f".{output.name}.staging-{os.getpid()}"
    if not quiesced:
        raise NativeRuntimeError("NATIVE_BACKUP_REQUIRES_QUIESCE")
    metadata = verify_install(target_root, expected_sha)
    state_root = _safe_root(target_root / "shared")
    if any(
        _is_within(candidate, state_root / component)
        for candidate in (output, staging)
        for component in ("files", "config")
    ):
        raise NativeRuntimeError("NATIVE_BACKUP_OUTPUT_RECURSIVE")
    pg_env, database_identity = _postgres_connection(database_url)
    dump_version = _postgres_tool_version("pg_dump")
    server_version = _postgres_server_version(database_url)
    if dump_version["major"] != server_version["major"]:
        raise NativeRuntimeError("NATIVE_POSTGRES_TOOL_VERSION_MISMATCH")
    database_settings = _postgres_database_settings(database_url)
    role_profile = _postgres_role_profile(database_url)
    readback_before = _postgres_readback(database_url)

    if staging.exists() or staging.is_symlink():
        raise NativeRuntimeError("NATIVE_BACKUP_STAGING_COLLISION")
    staging_created = False
    try:
        staging.mkdir(mode=0o700)
        staging_created = True
        (staging / "db").mkdir(mode=0o700)
        for name in ("files", "config"):
            _copy_backup_component(state_root / name, staging / name)
        archive = staging / POSTGRES_ARCHIVE
        _run(
            [
                "pg_dump", "--format=custom", "--no-owner", "--no-privileges",
                "--no-password", "--no-tablespaces", "--serializable-deferrable",
                "--file", str(archive),
            ],
            staging,
            pg_env,
            timeout=900,
        )
        if not archive.is_file() or archive.is_symlink() or archive.stat().st_size == 0:
            raise NativeRuntimeError("NATIVE_POSTGRES_ARCHIVE_INVALID")
        readback_after = _postgres_readback(database_url)
        if readback_after != readback_before:
            raise NativeRuntimeError("NATIVE_POSTGRES_QUIESCE_READBACK_CHANGED")
        if verify_install(target_root, expected_sha) != metadata:
            raise NativeRuntimeError("NATIVE_INSTALL_READBACK_FAILED")
        manifest = {
            "schema_version": POSTGRES_BACKUP_SCHEMA_VERSION,
            "database_adapter": "postgresql",
            "quiesced": True,
            "contains_secrets": True,
            "source_identity": {
                "repository": metadata["repository"],
                "source_sha": metadata["source_sha"],
                "source_release_manifest_sha256": metadata["source_release_manifest_sha256"],
                "application_tree_sha256": metadata["application_tree_sha256"],
            },
            "database": {
                "archive": POSTGRES_ARCHIVE.as_posix(),
                "format": "custom",
                "server_version_num": server_version["version_num"],
                "server_major": server_version["major"],
                "pg_dump_version": dump_version["version"],
                "pg_dump_major": dump_version["major"],
                "source_identity_sha256": database_identity,
                "database_settings": database_settings,
                "role_profile": role_profile,
            },
            "components": POSTGRES_COMPONENTS,
            "application_readback": readback_before,
            "files_sha256": _backup_hashes(staging),
        }
        _harden_backup_tree(staging)
        (staging / "manifest.json").write_bytes(_canonical_json(manifest))
        (staging / "manifest.json").chmod(0o600)
        verify_backup(staging, expected_sha)
        staging.rename(output)
    except Exception:
        if staging_created:
            shutil.rmtree(staging, ignore_errors=True)
        raise
    return verify_backup(output, expected_sha)


def restore_sqlite(backup_root: Path, target_state: Path) -> dict:
    backup_root = _safe_root(backup_root)
    target_state = Path(target_state)
    if not target_state.is_absolute() or target_state.exists() or target_state.is_symlink():
        raise NativeRuntimeError("NATIVE_RESTORE_TARGET_INVALID")
    _safe_root(target_state.parent)
    staging = target_state.parent / f".{target_state.name}.staging-{os.getpid()}"
    if any(_is_within(candidate, backup_root) for candidate in (target_state, staging)):
        raise NativeRuntimeError("NATIVE_RESTORE_TARGET_INSIDE_BACKUP")
    manifest = verify_backup(backup_root)
    if staging.exists() or staging.is_symlink():
        raise NativeRuntimeError("NATIVE_RESTORE_STAGING_COLLISION")
    staging_created = False
    try:
        staging.mkdir(mode=0o700)
        staging_created = True
        for name in ("db", "files", "config"):
            _copy_backup_component(backup_root / name, staging / name)
        if _backup_hashes(staging) != manifest["files_sha256"]:
            raise NativeRuntimeError("NATIVE_SQLITE_RESTORE_STAGING_HASH_MISMATCH")
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
        if staging_created:
            shutil.rmtree(staging, ignore_errors=True)
        raise
    return manifest


def restore_postgresql(
    backup_root: Path,
    target_state: Path,
    expected_sha: str,
    database_url: str,
) -> dict:
    backup_root = _safe_root(backup_root)
    target_state = Path(target_state)
    expected_sha = _sha(expected_sha)
    if not target_state.is_absolute() or target_state.exists() or target_state.is_symlink():
        raise NativeRuntimeError("NATIVE_RESTORE_TARGET_INVALID")
    _safe_root(target_state.parent)
    staging = target_state.parent / f".{target_state.name}.staging-{os.getpid()}"
    if any(_is_within(candidate, backup_root) for candidate in (target_state, staging)):
        raise NativeRuntimeError("NATIVE_RESTORE_TARGET_INSIDE_BACKUP")
    # Manifesto, SHA, hashes e TOC são verificados antes de qualquer conexão
    # com o destino ou criação do staging.
    manifest_path = backup_root / "manifest.json"
    manifest, manifest_sha256 = _read_json_with_sha256(manifest_path)
    manifest = _verify_backup_manifest(backup_root, manifest, expected_sha)
    if _hash_file(manifest_path) != manifest_sha256:
        raise NativeRuntimeError("NATIVE_BACKUP_MANIFEST_CHANGED")
    pg_env, target_identity = _postgres_connection(database_url)
    if target_identity == manifest["database"]["source_identity_sha256"]:
        raise NativeRuntimeError("NATIVE_POSTGRES_RESTORE_SOURCE_TARGET_EQUAL")
    target_server = _postgres_server_version(database_url)
    if target_server["major"] != manifest["database"]["server_major"]:
        raise NativeRuntimeError("NATIVE_POSTGRES_SERVER_VERSION_MISMATCH")
    if _postgres_database_settings(database_url) != manifest["database"]["database_settings"]:
        raise NativeRuntimeError("NATIVE_POSTGRES_DATABASE_SETTINGS_MISMATCH")
    if _postgres_role_profile(database_url) != manifest["database"]["role_profile"]:
        raise NativeRuntimeError("NATIVE_POSTGRES_ROLE_PROFILE_MISMATCH")
    target_dump_version = _postgres_tool_version("pg_dump")
    if target_dump_version["major"] != target_server["major"]:
        raise NativeRuntimeError("NATIVE_POSTGRES_TOOL_VERSION_MISMATCH")
    _require_postgres_pristine_target(database_url, target_state.parent)

    if staging.exists() or staging.is_symlink():
        raise NativeRuntimeError("NATIVE_RESTORE_STAGING_COLLISION")
    staging_created = False
    try:
        staging.mkdir(mode=0o700)
        staging_created = True
        for name in ("db", "files", "config"):
            _copy_backup_component(backup_root / name, staging / name)
        for name in ("tmp", "log", "backups"):
            (staging / name).mkdir(mode=0o700)
        archive = staging / POSTGRES_ARCHIVE
        if _backup_hashes(staging) != manifest["files_sha256"]:
            raise NativeRuntimeError("NATIVE_POSTGRES_RESTORE_STAGING_HASH_MISMATCH")
        _require_postgres_pristine_target(database_url, target_state.parent)
        if _hash_file(manifest_path) != manifest_sha256:
            raise NativeRuntimeError("NATIVE_BACKUP_MANIFEST_CHANGED")
        if _backup_hashes(staging) != manifest["files_sha256"]:
            raise NativeRuntimeError("NATIVE_POSTGRES_RESTORE_STAGING_HASH_MISMATCH")
        _run(
            [
                "pg_restore", "--exit-on-error", "--single-transaction",
                "--no-owner", "--no-privileges", "--no-password", "--no-tablespaces",
                "--dbname", pg_env["PGDATABASE"],
                str(archive),
            ],
            backup_root,
            pg_env,
            timeout=900,
        )
        try:
            archive.unlink()
        except OSError:
            raise NativeRuntimeError("NATIVE_POSTGRES_ARCHIVE_CLEANUP_FAILED") from None
        restored_readback = _postgres_readback(database_url)
        if restored_readback != manifest["application_readback"]:
            raise NativeRuntimeError("NATIVE_POSTGRES_RESTORE_READBACK_MISMATCH")
        expected_components = {
            path: digest
            for path, digest in manifest["files_sha256"].items()
            if path.startswith("files/") or path.startswith("config/")
        }
        actual_components = {
            path: digest
            for path, digest in _backup_hashes(staging).items()
            if path.startswith("files/") or path.startswith("config/")
        }
        if actual_components != expected_components:
            raise NativeRuntimeError("NATIVE_POSTGRES_RESTORE_COMPONENT_MISMATCH")
        receipt = {
            "schema_version": 1,
            "database_adapter": "postgresql",
            "source_sha": manifest["source_identity"]["source_sha"],
            "backup_manifest_sha256": manifest_sha256,
            "target_database_identity_sha256": target_identity,
            "application_readback": restored_readback,
        }
        (staging / POSTGRES_RESTORE_RECEIPT).write_bytes(_canonical_json(receipt))
        _harden_backup_tree(staging)
        if _read_json(staging / POSTGRES_RESTORE_RECEIPT) != receipt:
            raise NativeRuntimeError("NATIVE_POSTGRES_RESTORE_RECEIPT_READBACK_FAILED")
        staging.rename(target_state)
    except Exception:
        if staging_created:
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

    backup_pg = sub.add_parser("backup-postgresql")
    backup_pg.add_argument("--target-root", required=True)
    backup_pg.add_argument("--output", required=True)
    backup_pg.add_argument("--expected-sha", required=True)
    backup_pg.add_argument("--quiesced", action="store_true")

    check_backup = sub.add_parser("verify-backup")
    check_backup.add_argument("--backup-root", required=True)
    check_backup.add_argument("--expected-sha")

    restore = sub.add_parser("restore-sqlite")
    restore.add_argument("--backup-root", required=True)
    restore.add_argument("--target-state", required=True)

    restore_pg = sub.add_parser("restore-postgresql")
    restore_pg.add_argument("--backup-root", required=True)
    restore_pg.add_argument("--target-state", required=True)
    restore_pg.add_argument("--expected-sha", required=True)

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
        elif args.action == "backup-postgresql":
            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                raise NativeRuntimeError("NATIVE_POSTGRES_URL_REQUIRED")
            payload = backup_postgresql(
                Path(args.target_root),
                Path(args.output),
                args.expected_sha,
                database_url,
                quiesced=args.quiesced,
            )
        elif args.action == "verify-backup":
            payload = verify_backup(Path(args.backup_root), args.expected_sha)
        elif args.action == "restore-sqlite":
            payload = restore_sqlite(Path(args.backup_root), Path(args.target_state))
        else:
            database_url = os.environ.get("REQSYS_RESTORE_DATABASE_URL")
            if not database_url:
                raise NativeRuntimeError("NATIVE_POSTGRES_URL_REQUIRED")
            payload = restore_postgresql(
                Path(args.backup_root),
                Path(args.target_state),
                args.expected_sha,
                database_url,
            )
    except NativeRuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
