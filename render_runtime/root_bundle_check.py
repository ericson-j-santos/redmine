"""Resolve ou valida o bundle da raiz em worktree GitHub hospedado descartável."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import secrets
import signal
import subprocess
import tempfile

SOURCE_GEMFILE_BLOB = "13c53d168aac6b2a99ec07ac9fbd5ce0979e1f5d"
REPLACEMENTS = {
    "gem 'rails', '8.0.3'": "gem 'rails', '8.0.5.1'",
    "gem 'mail', '~> 2.8.1'": "gem 'mail', '2.9.1'",
    "gem 'nokogiri', '~> 1.18.3'": "gem 'nokogiri', '~> 1.19.4'",
    "gem 'rubyzip', '~> 3.1.1'": "gem 'rubyzip', '3.4.1'",
    "gem 'sqlite3', '~> 2.7.4'": "gem 'sqlite3', '~> 2.9.6'",
}
UPDATE = (
    "rails mail nokogiri rubyzip sqlite3 addressable bcrypt concurrent-ruby "
    "crass css_parser erb faraday json jwt loofah net-imap oauth2 puma rack "
    "rack-session rails-html-sanitizer websocket-driver yard roadie"
).split()


def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def candidate_gemfile(raw: bytes) -> bytes:
    if blob_sha(raw) != SOURCE_GEMFILE_BLOB:
        raise ValueError("ROOT_GEMFILE_SOURCE_CHANGED")
    text = raw.decode("utf-8")
    for old, new in REPLACEMENTS.items():
        if text.count(old) != 1:
            raise ValueError("ROOT_GEMFILE_DECLARATION_AMBIGUOUS")
        text = text.replace(old, new)
    return text.encode()


def require_suite(text: str) -> dict[str, int]:
    matches = re.findall(
        r"(?m)^\s*(\d+) runs, (\d+) assertions, (\d+) failures, (\d+) errors, (\d+) skips\s*$",
        text,
    )
    if len(matches) != 1:
        raise ValueError("ROOT_SUITE_SUMMARY_INVALID")
    result = dict(zip(("runs", "assertions", "failures", "errors", "skips"), map(int, matches[0])))
    if result["runs"] < 5 or result["assertions"] < 5 or any(
        result[key] for key in ("failures", "errors", "skips")
    ):
        raise ValueError("ROOT_SUITE_NOT_PASSED")
    return result


def require_frozen_rejection(code: int, output: str) -> None:
    """Só aceita a recusa real do Bundler por divergência Gemfile/lock."""
    if (code != 16 or not isinstance(output, str)
            or not any(word in output.lower() for word in ("frozen", "deployment mode"))):
        raise ValueError("ROOT_FROZEN_CONTROL_FAILED")



def require_metadata_only_change(original: bytes, updated: bytes) -> str:
    """Aceita somente metadado Ruby nativo novo; nenhuma gem pode mudar."""
    pattern = rb"(?m)^RUBY VERSION\n   ruby ([0-9]+\.[0-9]+\.[0-9]+(?:p-?[0-9]+)?)\n\n"
    before = list(re.finditer(pattern, original))
    after = list(re.finditer(pattern, updated))
    if len(before) != 1 or len(after) != 1:
        raise ValueError("ROOT_RUBY_METADATA_INVALID")
    if re.sub(pattern, b"RUBY VERSION\n\n", original) != re.sub(
        pattern, b"RUBY VERSION\n\n", updated
    ):
        raise ValueError("ROOT_RUBY_METADATA_CHANGED_DEPENDENCIES")
    version = after[0].group(1).decode()
    if version.split(".")[:2] not in (["3", "3"], ["3", "4"]):
        raise ValueError("ROOT_RUBY_METADATA_UNSUPPORTED")
    return version


OBSERVER_GEMFILE_BLOB = "a75c8581db8556da531998e136eb9e3ec66a0f3c"
OBSERVER_LOCK_BLOB = "74f0bf582977eafef79753a0ae63f11413cfd37c"
OBSERVER_LINE = b"  gem 'observer', '0.1.2', require: false\n"


def observer_candidate_gemfile(raw: bytes) -> bytes:
    """Adiciona somente a dependência de teste à fonte conhecida."""
    if blob_sha(raw) != OBSERVER_GEMFILE_BLOB:
        raise ValueError("ROOT_OBSERVER_SOURCE_CHANGED")
    marker = b"group :test do\n"
    if raw.count(marker) != 1 or b"gem 'observer'" in raw:
        raise ValueError("ROOT_OBSERVER_DECLARATION_AMBIGUOUS")
    return raw.replace(marker, marker + OBSERVER_LINE, 1)


def require_observer_only_change(original: bytes, updated: bytes) -> None:
    """Nenhuma versão, plataforma, origem ou metadado existente pode mudar."""
    for line in (b"    observer (0.1.2)\n", b"  observer (= 0.1.2)\n"):
        if line in original or updated.count(line) != 1:
            raise ValueError("ROOT_OBSERVER_LOCK_INVALID")
        updated = updated.replace(line, b"", 1)
    if updated != original:
        raise ValueError("ROOT_OBSERVER_CHANGED_EXISTING_LOCK")


def require_observer_contract(gemfile: bytes, lock: bytes) -> None:
    if gemfile.count(OBSERVER_LINE) != 1 or b"group :test do\n" + OBSERVER_LINE not in gemfile:
        raise ValueError("ROOT_OBSERVER_TEST_DEPENDENCY_MISSING")
    for line in (b"    observer (0.1.2)\n", b"  observer (= 0.1.2)\n"):
        if lock.count(line) != 1:
            raise ValueError("ROOT_OBSERVER_LOCK_INVALID")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("candidate", "verify", "ruby-metadata", "observer-candidate", "database-candidate"))
    mode = parser.parse_args().mode
    if (os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or os.environ.get("GITHUB_REPOSITORY") != "ericson-j-santos/redmine"
            or os.environ.get("GITHUB_REF") !=
            "refs/heads/dev/reqsys-e2e-redmine-6.1.4-20260928"):
        raise SystemExit("ROOT_BUNDLE_SCOPE_REJECTED")
    sha = os.environ.get("GITHUB_SHA", "")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise SystemExit("ROOT_BUNDLE_SHA_INVALID")
    source = Path.cwd().resolve()
    observed = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    origin = subprocess.check_output(["git", "remote", "get-url", "origin"], text=True).strip()
    if observed != sha or origin.removesuffix(".git") != "https://github.com/ericson-j-santos/redmine":
        raise SystemExit("ROOT_BUNDLE_SOURCE_MISMATCH")
    subprocess.run(["git", "diff", "--exit-code", "HEAD"], check=True, timeout=10)
    base = Path(tempfile.mkdtemp(prefix="root-bundle-", dir=os.environ["RUNNER_TEMP"])).resolve()
    root = base / "source"
    subprocess.run(["git", "worktree", "add", "--detach", str(root), sha], check=True, timeout=30)
    home = base / "home"
    home.mkdir(mode=0o700)
    secret = secrets.token_hex(64)
    env = {key: os.environ[key] for key in (
        "PATH", "LANG", "LC_ALL", "GEM_HOME", "GEM_PATH", "SSL_CERT_FILE", "SSL_CERT_DIR"
    ) if key in os.environ}
    env.update({
        "HOME": str(home), "BUNDLE_IGNORE_CONFIG": "1", "BUNDLE_PATH": str(base / "gems"),
        "BUNDLE_GEMFILE": str(root / "Gemfile"), "BUNDLE_WITHOUT": "development",
        "BUNDLE_FROZEN": "true" if mode == "verify" else "false",
        "BUNDLE_DEPLOYMENT": "false", "RAILS_ENV": "test", "SECRET_KEY_BASE": secret,
        "REDMINE_LANG": "en", "RAILS_MAX_THREADS": "1", "CI": "1",
        "RUNNER_TEMP": str(base),
    })
    (root / "config/database.yml").write_text(
        "test:\n  adapter: sqlite3\n  database: db/root_bundle_test.sqlite3\n"
        "  pool: 1\n  timeout: 5000\n", encoding="utf-8"
    )

    def run(args: list[str], stage: str, timeout: int = 180, *, reject_frozen: bool = False) -> str:
        print(f"ROOT_BUNDLE_STAGE stage={stage} sha={sha}", flush=True)
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stream:
            proc = subprocess.Popen(args, cwd=root, env=env, stdout=stream,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=10)
                raise SystemExit(f"ROOT_BUNDLE_TIMEOUT stage={stage}") from None
            stream.seek(0)
            output = stream.read().replace(secret, "[REDACTED]")
        print("\n".join(output.splitlines()[-100:]), flush=True)
        if reject_frozen:
            require_frozen_rejection(code, output)
        elif code:
            raise SystemExit(f"ROOT_BUNDLE_FAILED stage={stage} exit={code}")
        return output

    if mode == "candidate":
        target = root / "Gemfile"
        target.write_bytes(candidate_gemfile(target.read_bytes()))
        run(["bundle", "lock", "--update", *UPDATE], "resolve", 180)
        # Text transport only: no credentials, artifacts, pushes or automatic approvals.
        lock = (root / "Gemfile.lock").read_bytes()
        if len(lock) > 100_000 or "https://rubygems.org/" not in lock.decode():
            raise SystemExit("ROOT_LOCK_OUTPUT_INVALID")
        print("ROOT_CANDIDATE_GEMFILE_JSON=" + json.dumps(target.read_text()), flush=True)
        print("ROOT_CANDIDATE_LOCK_JSON=" + json.dumps(lock.decode()), flush=True)
        print("ROOT_CANDIDATE_LOCK_SHA256=" + hashlib.sha256(lock).hexdigest(), flush=True)
    if mode == "ruby-metadata":
        original_lock = (root / "Gemfile.lock").read_bytes()
        if blob_sha(original_lock) != "62521bc62544435cef3a2739afb414dc550781ee":
            raise SystemExit("ROOT_RUBY_METADATA_SOURCE_CHANGED")
        run(["bundle", "update", "--ruby"], "ruby_metadata", 240)
        updated_lock = (root / "Gemfile.lock").read_bytes()
        ruby_metadata = require_metadata_only_change(original_lock, updated_lock)
        print("ROOT_NATIVE_RUBY_METADATA=" + ruby_metadata, flush=True)
        print("ROOT_NATIVE_RUBY_LOCK_SHA256=" + hashlib.sha256(updated_lock).hexdigest(), flush=True)
        print("ROOT_NATIVE_RUBY_LOCK_BLOB=" + blob_sha(updated_lock), flush=True)
    if mode == "observer-candidate":
        target = root / "Gemfile"
        original_lock = (root / "Gemfile.lock").read_bytes()
        if blob_sha(original_lock) != OBSERVER_LOCK_BLOB:
            raise SystemExit("ROOT_OBSERVER_LOCK_SOURCE_CHANGED")
        target.write_bytes(observer_candidate_gemfile(target.read_bytes()))
        # Native resolver keeps existing resolutions; no update/unfreeze in verify.
        run(["bundle", "lock"], "observer_resolve", 180)
        updated_lock = (root / "Gemfile.lock").read_bytes()
        require_observer_only_change(original_lock, updated_lock)
        import difflib
        print("ROOT_OBSERVER_NATIVE_DIFF_JSON=" + json.dumps(list(difflib.unified_diff(
            original_lock.decode().splitlines(True), updated_lock.decode().splitlines(True),
            fromfile="Gemfile.lock.before", tofile="Gemfile.lock.after"
        ))), flush=True)
        print("ROOT_OBSERVER_NATIVE_LOCK_SHA256=" + hashlib.sha256(updated_lock).hexdigest(), flush=True)
        print("ROOT_OBSERVER_NATIVE_LOCK_BLOB=" + blob_sha(updated_lock), flush=True)
    if mode == "database-candidate":
        database_contract = runpy.run_path(str(root / "render_runtime/database_bundle_contract.py"))
        target = root / "Gemfile"
        original_lock = (root / "Gemfile.lock").read_bytes()
        if blob_sha(original_lock) != database_contract["SOURCE_LOCK_BLOB"]:
            raise SystemExit("ROOT_DATABASE_LOCK_SOURCE_CHANGED")
        target.write_bytes(database_contract["candidate_gemfile"](target.read_bytes()))
        run(["ruby", "-e", database_contract["BUNDLER_DSL_PROBE"]],
            "database_gemfile_matrix_contract", 30)
        # Resolver nativo, sem --update; a verificação normal permanece congelada.
        run(["bundle", "lock"], "database_resolve", 180)
        updated_lock = (root / "Gemfile.lock").read_bytes()
        database_contract["require_database_only_additions"](original_lock, updated_lock)
        database_contract["require_database_contract"](updated_lock)
        print("ROOT_DATABASE_ADDITIVE_LOCK_OK", flush=True)
    if mode in ("observer-candidate", "database-candidate", "verify"):
        require_observer_contract((root / "Gemfile").read_bytes(),
                                  (root / "Gemfile.lock").read_bytes())
    initial_lock = (root / "Gemfile.lock").read_bytes()
    env["BUNDLE_FROZEN"] = "true"
    run(["bundle", "install", "--jobs", "4", "--retry", "1"], "install", 240)
    if (root / "Gemfile.lock").read_bytes() != initial_lock:
        raise SystemExit("ROOT_LOCK_CHANGED_DURING_INSTALL")
    run(["bundle", "check"], "frozen_replay", 30)
    gemfile = root / "Gemfile"
    before_control = gemfile.read_bytes()
    pin = b"gem 'rails', '8.0.5.1'"
    if before_control.count(pin) != 1:
        raise SystemExit("ROOT_FROZEN_CONTROL_PIN_MISSING")
    try:
        gemfile.write_bytes(before_control.replace(pin, b"gem 'rails', '8.0.3'"))
        run(["bundle", "install", "--local"], "frozen_negative_control", 30,
            reject_frozen=True)
    finally:
        gemfile.write_bytes(before_control)
    if (root / "Gemfile.lock").read_bytes() != initial_lock:
        raise SystemExit("ROOT_LOCK_CHANGED_BY_NEGATIVE_CONTROL")
    run(["bundle", "check"], "restored_frozen_replay", 30)
    if mode in ("observer-candidate", "database-candidate", "verify"):
        run(["bundle", "exec", "ruby", "-e",
             "require 'active_support'; require 'factory_bot'; "
             "abort 'OBSERVER_NOT_RESOLVED' unless Gem.loaded_specs.fetch('observer').version.to_s == '0.1.2'; "
             "abort 'FACTORY_BOT_NOT_LOADED' unless defined?(FactoryBot::Factory); "
             "puts 'ROOT_FACTORY_BOT_OBSERVER_BOOT_OK ruby=' + RUBY_VERSION"],
            "factory_bot_observer_boot", 30)
        try:
            gemfile.write_bytes(before_control.replace(OBSERVER_LINE, b"", 1))
            run(["bundle", "install", "--local"], "observer_frozen_negative_control", 30,
                reject_frozen=True)
        finally:
            gemfile.write_bytes(before_control)
        if (root / "Gemfile.lock").read_bytes() != initial_lock:
            raise SystemExit("ROOT_OBSERVER_CONTROL_CHANGED_LOCK")
        run(["bundle", "check"], "observer_restored_replay", 30)
    if mode == "database-candidate":
        declaration = b"    gem 'mysql2', '~> 0.5.0', require: false\n"
        if before_control.count(declaration) != 1:
            raise SystemExit("ROOT_DATABASE_NEGATIVE_CONTROL_AMBIGUOUS")
        try:
            gemfile.write_bytes(before_control.replace(declaration, b"", 1))
            run(["bundle", "install", "--local"], "database_frozen_negative_control", 30,
                reject_frozen=True)
        finally:
            gemfile.write_bytes(before_control)
        if (root / "Gemfile.lock").read_bytes() != initial_lock:
            raise SystemExit("ROOT_DATABASE_CONTROL_CHANGED_LOCK")
        run(["bundle", "check"], "database_restored_replay", 30)
        run(["ruby", "-e", database_contract["BUNDLER_DSL_PROBE"]],
            "database_contract_restored_replay", 30)
    run(["bundle", "exec", "bundle", "audit", "check", "--update"], "audit", 120)
    run(["bundle", "exec", "rails", "db:migrate"], "migrate", 120)
    suites = {}
    for suite, path in (
        ("attachment", "test/unit/attachment_test.rb"),
        ("mailer", "test/unit/mailer_test.rb"),
        ("spent_hours_model", "test/unit/models/spent_hours_model_test.rb"),
        ("spent_hours_integration", "test/integration/spent_hours_integration_test.rb"),
    ):
        text = run(["bundle", "exec", "ruby", "-Itest", path],
                   suite, 180)
        suites[suite] = require_suite(text)
    if (root / "Gemfile.lock").read_bytes() != initial_lock:
        raise SystemExit("ROOT_LOCK_CHANGED_DURING_TESTS")
    if mode == "database-candidate":
        print("ROOT_DATABASE_NATIVE_GEMFILE_JSON=" + json.dumps(gemfile.read_text()), flush=True)
        print("ROOT_DATABASE_NATIVE_LOCK_JSON=" + json.dumps(initial_lock.decode()), flush=True)
        print("ROOT_DATABASE_NATIVE_LOCK_SHA256=" + hashlib.sha256(initial_lock).hexdigest(), flush=True)
        print("ROOT_DATABASE_NATIVE_LOCK_BLOB=" + blob_sha(initial_lock), flush=True)
    print(json.dumps({
        "status": {"database-candidate": "database_candidate_validated_not_committed",
                   "observer-candidate": "observer_candidate_validated_not_committed",
                   "candidate": "candidate_validated_not_committed",
                   "ruby-metadata": "ruby_metadata_validated_not_committed",
                   "verify": "passed"}[mode],
        "sha": sha, "scope": "root_source_isolated_not_deployed",
        "lock_sha256": hashlib.sha256(initial_lock).hexdigest(), "suites": suites,
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
