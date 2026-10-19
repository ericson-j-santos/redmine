"""Resolve ou valida o bundle da raiz em worktree GitHub hospedado descartável."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("candidate", "verify"))
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
        "BUNDLE_FROZEN": "false" if mode == "candidate" else "true",
        "BUNDLE_DEPLOYMENT": "false", "RAILS_ENV": "test", "SECRET_KEY_BASE": secret,
        "REDMINE_LANG": "en", "RAILS_MAX_THREADS": "1", "CI": "1",
    })
    (root / "config/database.yml").write_text(
        "test:\n  adapter: sqlite3\n  database: db/root_bundle_test.sqlite3\n"
        "  pool: 1\n  timeout: 5000\n", encoding="utf-8"
    )

    def run(args: list[str], stage: str, timeout: int = 180) -> str:
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
        if code:
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
    initial_lock = (root / "Gemfile.lock").read_bytes()
    env["BUNDLE_FROZEN"] = "true"
    run(["bundle", "install", "--jobs", "4", "--retry", "1"], "install", 240)
    if (root / "Gemfile.lock").read_bytes() != initial_lock:
        raise SystemExit("ROOT_LOCK_CHANGED_DURING_INSTALL")
    run(["bundle", "check"], "frozen_replay", 30)
    run(["bundle", "exec", "bundle", "audit", "check", "--update"], "audit", 120)
    run(["bundle", "exec", "rails", "db:migrate"], "migrate", 120)
    suites = {}
    for suite in ("attachment", "mailer"):
        text = run(["bundle", "exec", "ruby", "-Itest", f"test/unit/{suite}_test.rb"],
                   suite, 180)
        suites[suite] = require_suite(text)
    if (root / "Gemfile.lock").read_bytes() != initial_lock:
        raise SystemExit("ROOT_LOCK_CHANGED_DURING_TESTS")
    print(json.dumps({
        "status": "candidate_validated_not_committed" if mode == "candidate" else "passed",
        "sha": sha, "scope": "root_source_isolated_not_deployed",
        "lock_sha256": hashlib.sha256(initial_lock).hexdigest(), "suites": suites,
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
