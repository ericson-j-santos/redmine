#!/usr/bin/env python3
"""E2E isolado do backup/restore PostgreSQL do runtime Linux nativo."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets

import native_runtime as native


POSTGRES_CONTENT_SQL = """
SELECT json_build_object(
  'project_name', (SELECT name FROM public.projects WHERE id = 1),
  'project_identifier', (SELECT identifier FROM public.projects WHERE id = 1),
  'issue_subject', (SELECT subject FROM public.issues WHERE id = 1),
  'user_login', (SELECT login FROM public.users WHERE id = 1),
  'attachment_filename', (SELECT filename FROM public.attachments WHERE id = 1),
  'attachment_disk_filename', (SELECT disk_filename FROM public.attachments WHERE id = 1),
  'attachment_container_type', (SELECT container_type FROM public.attachments WHERE id = 1),
  'attachment_content_type', (SELECT content_type FROM public.attachments WHERE id = 1)
)::text;
""".strip()


def fail(code: str) -> None:
    raise SystemExit(code)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_empty_database(url: str, label: str, working_directory: Path) -> None:
    try:
        native._require_postgres_pristine_target(url, working_directory)
    except native.NativeRuntimeError:
        fail(f"NATIVE_POSTGRES_E2E_{label}_NOT_EMPTY")


def database_content_readback(url: str) -> dict[str, str]:
    """Lê valores funcionais sem reutilizar o readback agregado do runtime."""
    try:
        payload = json.loads(native._postgres_query(url, POSTGRES_CONTENT_SQL))
    except (ValueError, UnicodeError):
        fail("NATIVE_POSTGRES_E2E_CONTENT_READBACK_INVALID")
    if not isinstance(payload, dict) or any(not isinstance(value, str) for value in payload.values()):
        fail("NATIVE_POSTGRES_E2E_CONTENT_READBACK_INVALID")
    return payload


def expected_database_content(marker: str) -> dict[str, str]:
    return {
        "project_name": f"ReqSys backup {marker}",
        "project_identifier": f"reqsys-backup-{marker}",
        "issue_subject": f"PostgreSQL backup {marker}",
        "user_login": f"reqsys-backup-{marker}",
        "attachment_filename": f"evidence-{marker}.txt",
        "attachment_disk_filename": marker,
        "attachment_container_type": "Issue",
        "attachment_content_type": "text/plain",
    }


def seed_minimal_redmine_database(url: str, marker: str) -> None:
    """Cria somente as relações necessárias ao readback independente do gate."""
    sql = f"""
    CREATE TABLE public.schema_migrations (
      version varchar(255) PRIMARY KEY
    );
    CREATE TABLE public.users (
      id bigint PRIMARY KEY,
      login varchar(255) NOT NULL UNIQUE
    );
    CREATE TABLE public.projects (
      id bigint PRIMARY KEY,
      name varchar(255) NOT NULL,
      identifier varchar(255) NOT NULL UNIQUE,
      status integer NOT NULL DEFAULT 1
    );
    CREATE TABLE public.issues (
      id bigint PRIMARY KEY,
      project_id bigint NOT NULL REFERENCES public.projects(id),
      subject varchar(255) NOT NULL,
      status_id integer NOT NULL DEFAULT 1,
      tracker_id integer NOT NULL DEFAULT 1,
      priority_id integer NOT NULL DEFAULT 1,
      author_id integer NOT NULL DEFAULT 1
    );
    CREATE TABLE public.attachments (
      id bigint PRIMARY KEY,
      container_id bigint NOT NULL,
      container_type varchar(30) NOT NULL,
      filename varchar(255) NOT NULL,
      disk_filename varchar(255) NOT NULL,
      filesize bigint NOT NULL,
      content_type varchar(255)
    );
    INSERT INTO public.projects(id, name, identifier, status)
      VALUES (1, 'ReqSys backup {marker}', 'reqsys-backup-{marker}', 1);
    INSERT INTO public.schema_migrations(version) VALUES ('20261022000000');
    INSERT INTO public.users(id, login) VALUES (1, 'reqsys-backup-{marker}');
    INSERT INTO public.issues(id, project_id, subject, status_id, tracker_id, priority_id, author_id)
      VALUES (1, 1, 'PostgreSQL backup {marker}', 1, 1, 1, 1);
    INSERT INTO public.attachments(
      id, container_id, container_type, filename, disk_filename, filesize, content_type
    ) VALUES (
      1, 1, 'Issue', 'evidence-{marker}.txt', '{marker}', 32, 'text/plain'
    );
    """
    native._run_postgres_sql(url, sql)


def install_search_path_decoy(url: str) -> None:
    """Prova que readbacks não dependem do search_path configurado no banco."""
    native._run_postgres_sql(
        url,
        """
        CREATE SCHEMA reqsys_decoy;
        CREATE TABLE reqsys_decoy.schema_migrations(version varchar(255));
        CREATE TABLE reqsys_decoy.projects(id bigint, name varchar(255), identifier varchar(255));
        CREATE TABLE reqsys_decoy.issues(id bigint, subject varchar(255));
        CREATE TABLE reqsys_decoy.users(id bigint, login varchar(255));
        CREATE TABLE reqsys_decoy.attachments(
          id bigint,
          filename varchar(255),
          disk_filename varchar(255),
          container_type varchar(30),
          content_type varchar(255)
        );
        INSERT INTO reqsys_decoy.schema_migrations VALUES ('99999999999999');
        INSERT INTO reqsys_decoy.projects VALUES (99, 'decoy', 'decoy');
        INSERT INTO reqsys_decoy.issues VALUES (99, 'decoy');
        INSERT INTO reqsys_decoy.users VALUES (99, 'decoy');
        INSERT INTO reqsys_decoy.attachments VALUES (99, 'decoy', 'decoy', 'Decoy', 'text/decoy');
        """,
    )
    database_name = native._postgres_query(url, "SELECT current_database();")
    if not database_name or "\x00" in database_name:
        fail("NATIVE_POSTGRES_E2E_DATABASE_NAME_INVALID")
    quoted_database = database_name.replace('"', '""')
    native._run_postgres_sql(
        url,
        f'ALTER DATABASE "{quoted_database}" SET search_path = reqsys_decoy, public;',
    )
    if native._postgres_query(url, "SELECT max(id)::text FROM projects;") != "99":
        fail("NATIVE_POSTGRES_E2E_SEARCH_PATH_DECOY_INACTIVE")


def assert_restored_state(
    source_snapshot: dict,
    expected_content: dict[str, str],
    database_url: str,
    state: Path,
    attachment_relative: Path,
    attachment_sha: str,
    config_relative: Path,
    config_sha: str,
) -> None:
    if native._postgres_readback(database_url) != source_snapshot:
        fail("NATIVE_POSTGRES_E2E_DATABASE_READBACK_MISMATCH")
    if database_content_readback(database_url) != expected_content:
        fail("NATIVE_POSTGRES_E2E_DATABASE_CONTENT_MISMATCH")
    if file_sha256(state / "files" / attachment_relative) != attachment_sha:
        fail("NATIVE_POSTGRES_E2E_ATTACHMENT_READBACK_MISMATCH")
    if file_sha256(state / "config" / config_relative) != config_sha:
        fail("NATIVE_POSTGRES_E2E_CONFIG_READBACK_MISMATCH")
    if (state / native.POSTGRES_ARCHIVE).exists():
        fail("NATIVE_POSTGRES_E2E_RESTORED_STATE_RETAINED_DUMP")
    if not (state / native.POSTGRES_RESTORE_RECEIPT).is_file():
        fail("NATIVE_POSTGRES_E2E_RESTORE_RECEIPT_MISSING")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-root", required=True)
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args()

    target = Path(args.target_root).resolve()
    expected_sha = args.expected_sha
    source_url = os.environ.get("DATABASE_URL", "")
    restore_url = os.environ.get("REQSYS_RESTORE_DATABASE_URL", "")
    replay_url = os.environ.get("REQSYS_REPLAY_DATABASE_URL", "")
    if not source_url or not restore_url or not replay_url:
        fail("NATIVE_POSTGRES_E2E_DATABASE_URLS_REQUIRED")
    if len({source_url, restore_url, replay_url}) != 3:
        fail("NATIVE_POSTGRES_E2E_DATABASE_URLS_NOT_DISTINCT")

    native.verify_install(target, expected_sha)
    for url, label in (
        (source_url, "SOURCE"),
        (restore_url, "RESTORE"),
        (replay_url, "REPLAY"),
    ):
        try:
            native._postgres_role_profile(url)
        except native.NativeRuntimeError:
            fail(f"NATIVE_POSTGRES_E2E_{label}_ROLE_NOT_RESTRICTED")
        require_empty_database(url, label, target.parent)

    marker = secrets.token_hex(12)
    seed_minimal_redmine_database(source_url, marker)
    install_search_path_decoy(source_url)
    source_snapshot = native._postgres_readback(source_url)
    expected_content = expected_database_content(marker)
    if min(
        source_snapshot.get(name, 0)
        for name in (
            "schema_migrations_count",
            "projects_count",
            "issues_count",
            "attachments_count",
            "users_count",
        )
    ) != 1:
        fail("NATIVE_POSTGRES_E2E_SEED_READBACK_FAILED")
    if database_content_readback(source_url) != expected_content:
        fail("NATIVE_POSTGRES_E2E_SEED_CONTENT_READBACK_FAILED")

    shared = target / "shared"
    attachment_relative = Path("e2e-postgresql") / f"{marker}.txt"
    attachment = shared / "files" / attachment_relative
    attachment.parent.mkdir(parents=True, exist_ok=True)
    attachment.write_text(f"postgresql backup evidence {marker}\n", encoding="utf-8")
    config_relative = Path("e2e-postgresql-backup.json")
    config = shared / "config" / config_relative
    config.write_text(
        json.dumps({"marker": marker, "scope": "disposable-ci"}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    attachment_sha = file_sha256(attachment)
    config_sha = file_sha256(config)

    backup = shared / "backups" / "e2e-postgresql-backup"
    if backup.exists() or backup.is_symlink():
        fail("NATIVE_POSTGRES_E2E_BACKUP_ALREADY_EXISTS")
    manifest = native.backup_postgresql(
        target,
        backup,
        expected_sha,
        source_url,
        quiesced=True,
    )
    if native.verify_backup(backup, expected_sha) != manifest:
        fail("NATIVE_POSTGRES_E2E_BACKUP_READBACK_FAILED")

    dump = backup / "db/redmine.pgdump"
    original_dump = dump.read_bytes()
    dump.write_bytes(original_dump + b"\nCONTROL_TAMPER\n")
    try:
        try:
            native.verify_backup(backup, expected_sha)
        except native.NativeRuntimeError:
            pass
        else:
            fail("NATIVE_POSTGRES_E2E_DUMP_TAMPER_MISSED")
    finally:
        dump.write_bytes(original_dump)
    if native.verify_backup(backup, expected_sha) != manifest:
        fail("NATIVE_POSTGRES_E2E_BACKUP_REPAIR_FAILED")

    wrong_sha = ("0" if expected_sha[0] != "0" else "1") + expected_sha[1:]
    wrong_state = target.parent / "postgresql-wrong-sha-state"
    wrong_db_before = native._postgres_user_object_count(restore_url)
    try:
        native.restore_postgresql(
            backup,
            wrong_state,
            wrong_sha,
            restore_url,
        )
    except native.NativeRuntimeError:
        pass
    else:
        fail("NATIVE_POSTGRES_E2E_WRONG_SHA_CONTROL_MISSED")
    if wrong_state.exists() or native._postgres_user_object_count(restore_url) != wrong_db_before:
        fail("NATIVE_POSTGRES_E2E_WRONG_SHA_MUTATED_TARGET")

    restored = target.parent / "postgresql-restored-state"
    native.restore_postgresql(backup, restored, expected_sha, restore_url)
    assert_restored_state(
        source_snapshot,
        expected_content,
        restore_url,
        restored,
        attachment_relative,
        attachment_sha,
        config_relative,
        config_sha,
    )

    nonempty_state = target.parent / "postgresql-nonempty-db-state"
    nonempty_snapshot_before = native._postgres_readback(restore_url)
    try:
        native.restore_postgresql(backup, nonempty_state, expected_sha, restore_url)
    except native.NativeRuntimeError as exc:
        if str(exc) != "NATIVE_POSTGRES_RESTORE_TARGET_NOT_EMPTY":
            fail("NATIVE_POSTGRES_E2E_NONEMPTY_DATABASE_WRONG_FAILURE")
    else:
        fail("NATIVE_POSTGRES_E2E_NONEMPTY_DATABASE_ACCEPTED")
    if (
        nonempty_state.exists()
        or native._postgres_readback(restore_url) != nonempty_snapshot_before
        or database_content_readback(restore_url) != expected_content
    ):
        fail("NATIVE_POSTGRES_E2E_NONEMPTY_DATABASE_MUTATED")

    receipt = restored / native.POSTGRES_RESTORE_RECEIPT
    receipt_sha_before = file_sha256(receipt)
    restored_snapshot_before = native._postgres_readback(restore_url)
    try:
        native.restore_postgresql(backup, restored, expected_sha, restore_url)
    except native.NativeRuntimeError:
        pass
    else:
        fail("NATIVE_POSTGRES_E2E_REPLAY_EXISTING_TARGET_ACCEPTED")
    if (
        file_sha256(receipt) != receipt_sha_before
        or native._postgres_readback(restore_url) != restored_snapshot_before
    ):
        fail("NATIVE_POSTGRES_E2E_REPLAY_CHANGED_FIRST_RESTORE")

    replayed = target.parent / "postgresql-replayed-state"
    native.restore_postgresql(backup, replayed, expected_sha, replay_url)
    assert_restored_state(
        source_snapshot,
        expected_content,
        replay_url,
        replayed,
        attachment_relative,
        attachment_sha,
        config_relative,
        config_sha,
    )

    payload = {
        "status": "passed",
        "source_sha": expected_sha,
        "backup_manifest_sha256": file_sha256(backup / "manifest.json"),
        "database_adapter": manifest.get("database_adapter"),
        "database_readback": source_snapshot,
        "database_content_readback": True,
        "search_path_decoy_ignored": True,
        "database_role_restricted": True,
        "dump_tamper_blocked": True,
        "wrong_sha_blocked_before_mutation": True,
        "nonempty_database_blocked_intact": True,
        "existing_target_replay_blocked_intact": True,
        "fresh_target_replay_readback": True,
        "attachments_readback": True,
        "config_readback": True,
        "scope": "github_hosted_ephemeral_postgresql_not_permanent_host",
    }
    encoded = json.dumps(payload, sort_keys=True)
    if any(value in encoded for value in (source_url, restore_url, replay_url)):
        fail("NATIVE_POSTGRES_E2E_PAYLOAD_CONTAINS_DATABASE_URL")
    print("NATIVE_POSTGRESQL_BACKUP_E2E_OK " + encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
