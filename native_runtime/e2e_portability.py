#!/usr/bin/env python3
"""E2E do runtime Linux nativo usando um build Redmine real já aprovado."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import sqlite3
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener

import native_runtime as native


def sqlite_snapshot(path: Path) -> dict[str, int]:
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        if db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise SystemExit("NATIVE_E2E_SQLITE_INTEGRITY_FAILED")
        issue_count = db.execute("SELECT count(*) FROM issues").fetchone()[0]
        project_count = db.execute("SELECT count(*) FROM projects").fetchone()[0]
        if issue_count < 1 or project_count < 1:
            raise SystemExit("NATIVE_E2E_SEED_MISSING")
        return {"issue_count": issue_count, "project_count": project_count}
    finally:
        db.close()


def run_runner(release: Path, env: dict[str, str], expected_issues: int) -> None:
    command = [
        "bundle", "exec", "rails", "runner",
        f'abort "NATIVE_E2E_RAILS_DB_MISMATCH" unless Issue.count == {expected_issues}; '
        'print "NATIVE_RAILS_READBACK_OK"',
    ]
    result = subprocess.run(
        command, cwd=release, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        timeout=90, check=False,
    )
    if result.returncode or "NATIVE_RAILS_READBACK_OK" not in result.stdout:
        raise SystemExit("NATIVE_E2E_RAILS_READBACK_FAILED")


def sanitized_log_tail(log_path: Path, env: dict[str, str], max_chars: int = 8000) -> str:
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    for name, value in env.items():
        upper = name.upper()
        if (
            isinstance(value, str)
            and len(value) >= 4
            and any(token in upper for token in ("KEY", "TOKEN", "SECRET", "PASSWORD"))
        ):
            text = text.replace(value, "[REDACTED]")
    tail = "\n".join(text.splitlines()[-40:])
    return tail[-max_chars:]


def release_tree_snapshot(release: Path) -> dict[str, str]:
    snapshot = {}
    for path in native._relative_files(release, exclude=native.EXCLUDED_TREE):
        rel = path.relative_to(release).as_posix()
        if rel == native.NATIVE_METADATA.as_posix():
            continue
        snapshot[rel] = native._hash_file(path)
    return snapshot


def release_tree_drift(before: dict[str, str], after: dict[str, str]) -> dict[str, list[str]]:
    return {
        "added": sorted(set(after) - set(before)),
        "removed": sorted(set(before) - set(after)),
        "changed": sorted(key for key in set(before) & set(after) if before[key] != after[key]),
    }


def seal_release_for_runtime(release: Path) -> dict[str, int]:
    """Emula o ProtectSystem=strict sem seguir links para o estado compartilhado."""
    release = release.resolve()
    if not release.is_dir() or release.is_symlink():
        raise SystemExit("NATIVE_E2E_RELEASE_SEAL_ROOT_INVALID")
    paths = [release, *sorted(release.rglob("*"), key=lambda value: value.as_posix())]
    modes: dict[str, int] = {}
    for path in paths:
        if path.is_symlink():
            continue
        try:
            mode = path.stat().st_mode & 0o7777
            path.chmod(mode & ~0o222)
        except OSError:
            raise SystemExit("NATIVE_E2E_RELEASE_SEAL_FAILED") from None
        rel = "." if path == release else path.relative_to(release).as_posix()
        modes[rel] = mode
    return modes


def restore_release_modes(release: Path, modes: dict[str, int]) -> None:
    """Restaura somente os modos alterados pelo E2E para limpeza do runner descartável."""
    for rel, mode in modes.items():
        path = release if rel == "." else release / rel
        if path.is_symlink():
            continue
        try:
            path.chmod(mode)
        except OSError:
            raise SystemExit("NATIVE_E2E_RELEASE_MODE_RESTORE_FAILED") from None


def start_and_probe(release: Path, env: dict[str, str], log_path: Path) -> None:
    ready = False
    terminated_by_test = False
    with log_path.open("xb") as log:
        proc = subprocess.Popen(
            [str(release / "bin/reqsys-redmine-start")],
            cwd=release, env=env, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            opener = build_opener(ProxyHandler({}))
            url = f"http://127.0.0.1:{env['REDMINE_PORT']}/login"
            for _ in range(40):
                if proc.poll() is not None:
                    break
                try:
                    with opener.open(url, timeout=2) as response:
                        if response.status == 200:
                            ready = True
                            break
                except (HTTPError, URLError, TimeoutError, OSError):
                    pass
                time.sleep(0.5)
        finally:
            if proc.poll() is None:
                terminated_by_test = True
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()

    try:
        native.validate_service_shutdown(ready, terminated_by_test, proc.returncode)
    except native.NativeRuntimeError as exc:
        print(
            "NATIVE_E2E_SERVICE_DIAGNOSTIC "
            f"ready={str(ready).lower()} "
            f"terminated_by_test={str(terminated_by_test).lower()} "
            f"returncode={proc.returncode}",
            file=sys.stderr,
        )
        tail = sanitized_log_tail(log_path, env)
        if tail:
            print("NATIVE_E2E_SERVICE_LOG_TAIL_BEGIN", file=sys.stderr)
            print(tail, file=sys.stderr)
            print("NATIVE_E2E_SERVICE_LOG_TAIL_END", file=sys.stderr)
        raise SystemExit(str(exc)) from None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--target-root", required=True)
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args()

    source = Path(args.source).resolve()
    target = Path(args.target_root).resolve()
    sha = args.expected_sha
    native.verify_source_manifest(source, sha)
    seed_db = source / "tmp/reqsys_redmine_e2e.sqlite3"
    before = sqlite_snapshot(seed_db)

    metadata = native.install_release(
        source, target, sha,
        seed_sqlite=seed_db,
        install_bundle=True,
    )
    if native.verify_install(target, sha) != metadata:
        raise SystemExit("NATIVE_E2E_INSTALL_READBACK_FAILED")

    release = (target / "current").resolve()
    release_tree_before_runtime = release_tree_snapshot(release)
    release_modes = seal_release_for_runtime(release)
    if native.verify_install(target, sha) != metadata:
        raise SystemExit("NATIVE_E2E_SEALED_INSTALL_READBACK_FAILED")
    print(f"NATIVE_E2E_RELEASE_READ_ONLY paths={len(release_modes)}", flush=True)
    state_db = target / "shared/db/redmine.sqlite3"
    after_install = sqlite_snapshot(state_db)
    if after_install != before:
        raise SystemExit("NATIVE_E2E_STATE_SEED_MISMATCH")

    env = dict(os.environ)
    env.update({
        "DATABASE_URL": f"sqlite3:{state_db}",
        "REDMINE_BIND": "127.0.0.1",
        "REDMINE_PORT": "31873",
        "RAILS_ENV": "production",
        "SECRET_KEY_BASE": secrets.token_hex(64),
        "BUNDLE_GEMFILE": str(release / "Gemfile"),
        "BUNDLE_PATH": str(release / "vendor/bundle"),
        "BUNDLE_DEPLOYMENT": "true",
        "BUNDLE_FROZEN": "true",
        "BUNDLE_WITHOUT": "development:test",
    })
    run_runner(release, env, before["issue_count"])

    start_and_probe(release, env, target / "shared/log/native-e2e-first.log")
    if sqlite_snapshot(state_db) != before:
        raise SystemExit("NATIVE_E2E_RESTART_STATE_CHANGED")
    start_and_probe(release, env, target / "shared/log/native-e2e-second.log")
    if sqlite_snapshot(state_db) != before:
        raise SystemExit("NATIVE_E2E_SECOND_RESTART_STATE_CHANGED")

    backup = target / "shared/backups/e2e-backup"
    native.backup_sqlite(target / "shared", backup, quiesced=True)
    native.verify_backup(backup)
    db_backup = backup / "db/redmine.sqlite3"
    original = db_backup.read_bytes()
    db_backup.write_bytes(original + b"\nCONTROL_TAMPER\n")
    try:
        try:
            native.verify_backup(backup)
        except native.NativeRuntimeError:
            pass
        else:
            raise SystemExit("NATIVE_E2E_BACKUP_NEGATIVE_CONTROL_MISSED")
    finally:
        db_backup.write_bytes(original)
    native.verify_backup(backup)

    restored = target.parent / "restored-state"
    native.restore_sqlite(backup, restored)
    if sqlite_snapshot(restored / "db/redmine.sqlite3") != before:
        raise SystemExit("NATIVE_E2E_RESTORE_STATE_MISMATCH")

    release_tree_after_runtime = release_tree_snapshot(release)
    if release_tree_after_runtime != release_tree_before_runtime:
        print(
            "NATIVE_E2E_RELEASE_TREE_DRIFT "
            + json.dumps(release_tree_drift(release_tree_before_runtime, release_tree_after_runtime), sort_keys=True),
            file=sys.stderr,
        )

    replay = native.install_release(source, target, sha, seed_sqlite=seed_db, install_bundle=True)
    if replay != metadata or sqlite_snapshot(state_db) != before:
        raise SystemExit("NATIVE_E2E_INSTALL_REPLAY_FAILED")
    releases = [p for p in (target / "releases").iterdir() if p.is_dir() and not p.name.startswith(".")]
    if [p.name for p in releases] != [sha]:
        raise SystemExit("NATIVE_E2E_DUPLICATE_RELEASE")

    wrong_target = target.parent / "wrong-sha-target"
    wrong_sha = ("0" if sha[0] != "0" else "1") + sha[1:]
    try:
        native.install_release(source, wrong_target, wrong_sha, seed_sqlite=seed_db, install_bundle=True)
    except native.NativeRuntimeError:
        pass
    else:
        raise SystemExit("NATIVE_E2E_WRONG_SHA_CONTROL_MISSED")
    if wrong_target.exists():
        raise SystemExit("NATIVE_E2E_WRONG_SHA_MUTATED_TARGET")

    restore_release_modes(release, release_modes)

    payload = {
        "status": "passed",
        "source_sha": sha,
        "redmine_version": metadata.get("redmine_version"),
        "issue_count": before["issue_count"],
        "project_count": before["project_count"],
        "restart_cycles": 2,
        "idempotent_replay": True,
        "wrong_sha_blocked_before_target_write": True,
        "backup_negative_control": True,
        "restore_independent_sqlite_readback": True,
        "native_release_tree_sha256": metadata["application_tree_sha256"],
        "backup_manifest_sha256": hashlib.sha256((backup / "manifest.json").read_bytes()).hexdigest(),
        "scope": "github_hosted_native_linux_portability_not_permanent_host",
    }
    print("NATIVE_LINUX_PORTABILITY_E2E_OK " + json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
