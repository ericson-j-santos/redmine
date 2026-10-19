"""Pins revisados do runtime descartável; não substitui bundler-audit/E2E."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile

UPSTREAM_BLOB = "0db3edefdabf92e376c05a10c6bdaf48663fe16f"
PINS = {"mail": "2.9.1", "rubyzip": "3.4.1", "sqlite3": "2.9.6"}
OLD = {"mail": "~> 2.8.1", "rubyzip": "~> 2.4.0", "sqlite3": "~> 2.5.0"}


class DependencyPolicyError(ValueError):
    """Erro sanitizado, sem imprimir conteúdo de configuração."""


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def hardened_gemfile(raw: bytes) -> bytes:
    """Aceita somente o upstream exato ou seu patch completo, de forma idempotente."""
    if not isinstance(raw, bytes) or len(raw) > 16384:
        raise DependencyPolicyError("DEPENDENCY_GEMFILE_INVALID")
    original = raw
    for name, version in PINS.items():
        old = f"gem '{name}', '{OLD[name]}'".encode()
        new = f"gem '{name}', '{version}'".encode()
        if raw.count(new) == 1 and raw.count(old) == 0:
            original = original.replace(new, old)
        elif raw.count(old) != 1 or raw.count(new) != 0:
            raise DependencyPolicyError("DEPENDENCY_GEMFILE_CONTRACT_MISMATCH")
    if blob_sha(original) != UPSTREAM_BLOB:
        raise DependencyPolicyError("DEPENDENCY_UPSTREAM_BLOB_MISMATCH")
    patched = original
    for name, version in PINS.items():
        patched = patched.replace(
            f"gem '{name}', '{OLD[name]}'".encode(),
            f"gem '{name}', '{version}'".encode(),
        )
    if raw not in (original, patched):
        raise DependencyPolicyError("DEPENDENCY_PARTIAL_PATCH_REJECTED")
    return patched


def apply_pins(target: Path) -> bool:
    """Altera atomicamente um arquivo regular; lock exclusivo evita disputa/replay."""
    info = target.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise DependencyPolicyError("DEPENDENCY_TARGET_NOT_REGULAR")
    lock = target.with_name(".reqsys-dependency-pins.lock")
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise DependencyPolicyError("DEPENDENCY_PATCH_BUSY") from exc
    temporary = None
    try:
        os.close(lock_fd)
        raw = target.read_bytes()
        patched = hardened_gemfile(raw)
        if patched == raw:
            return False
        with tempfile.NamedTemporaryFile(
            prefix=".Gemfile-pins-", dir=target.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(patched)
            stream.flush()
            os.fsync(stream.fileno())
        # Revalidate before replace; never overwrite an externally changed file.
        now = target.lstat()
        if (now.st_dev, now.st_ino, now.st_nlink) != (info.st_dev, info.st_ino, 1):
            raise DependencyPolicyError("DEPENDENCY_TARGET_CHANGED")
        if target.read_bytes() != raw:
            raise DependencyPolicyError("DEPENDENCY_TARGET_CHANGED")
        os.replace(temporary, target)
        temporary = None
        if target.read_bytes() != patched:
            raise DependencyPolicyError("DEPENDENCY_PATCH_READBACK_FAILED")
        return True
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        lock.unlink()


def runtime_root() -> Path:
    if os.environ.get("REQSYS_REDMINE_EPHEMERAL_E2E") != "1":
        raise DependencyPolicyError("DEPENDENCY_EPHEMERAL_SCOPE_REQUIRED")
    root = Path(__file__).resolve().parents[1]
    reserved = root / ".runtime"
    runtime = reserved / "redmine-6.1.5"
    if reserved.is_symlink() or runtime.is_symlink() or not runtime.is_dir():
        raise DependencyPolicyError("DEPENDENCY_RUNTIME_PATH_INVALID")
    return runtime


def test_summary(text: str) -> dict[str, int]:
    matches = re.findall(
        r"(?m)^\s*(\d+) runs, (\d+) assertions, (\d+) failures, (\d+) errors, (\d+) skips\s*$",
        text,
    )
    if len(matches) != 1:
        raise DependencyPolicyError("DEPENDENCY_TEST_SUMMARY_MISSING_OR_AMBIGUOUS")
    result = dict(zip(("runs", "assertions", "failures", "errors", "skips"), map(int, matches[0])))
    if (result["runs"] - result["skips"] < 5 or result["assertions"] < 5
            or result["failures"] or result["errors"]):
        raise DependencyPolicyError("DEPENDENCY_TESTS_NOT_PASSED")
    return result


def verify_compatibility(runtime: Path) -> dict:
    raw = (runtime / "Gemfile").read_bytes()
    if hardened_gemfile(raw) != raw:
        raise DependencyPolicyError("DEPENDENCY_PATCH_NOT_APPLIED")
    observed = json.loads((runtime / "tmp/reqsys-loaded-gems.json").read_text(encoding="utf-8"))
    if not isinstance(observed, dict) or observed != PINS:
        raise DependencyPolicyError("DEPENDENCY_LOADED_VERSIONS_MISMATCH")
    lock = (runtime / "Gemfile.lock").read_bytes()
    text = lock.decode("utf-8")
    for name, version in PINS.items():
        versions = re.findall(rf"(?m)^    {re.escape(name)} \(([^)]+)\)$", text)
        if not versions or any(item.split("-", 1)[0] != version for item in versions):
            raise DependencyPolicyError("DEPENDENCY_LOCK_VERSIONS_MISMATCH")
    suites = {
        name: test_summary((runtime / f"tmp/reqsys-{name}-compat.log").read_text(encoding="utf-8"))
        for name in ("attachment", "mailer")
    }
    return {"scope": "isolated_dependency_compatibility_not_deploy", "versions": observed,
            "upstream_gemfile_blob": UPSTREAM_BLOB, "patched_gemfile_blob": blob_sha(raw),
            "lock_sha256": hashlib.sha256(lock).hexdigest(), "suites": suites}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("patch", "verify-compatibility"))
    args = parser.parse_args(argv)
    try:
        runtime = runtime_root()
        if args.action == "patch":
            changed = apply_pins(runtime / "Gemfile")
            print(json.dumps({"dependency_pins_applied": True, "changed": changed, "pins": PINS},
                             sort_keys=True))
        else:
            print(json.dumps(verify_compatibility(runtime), sort_keys=True))
    except (DependencyPolicyError, OSError, UnicodeError, ValueError) as exc:
        message = str(exc) if isinstance(exc, DependencyPolicyError) else "DEPENDENCY_POLICY_IO_OR_DATA_ERROR"
        parser.exit(2, message + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
