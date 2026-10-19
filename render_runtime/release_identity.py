"""Proveniência do build DEV e manifesto verificável; não autoriza publicação."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

REPOSITORY = "ericson-j-santos/redmine"
BRANCH = "dev/reqsys-e2e-redmine-6.1.4-20260928"
SERVICE_ID = "srv-dathlk2d0e5s73c5722g"
SOURCE_SCOPE = "tracked_build_source_not_deployment_authorization"
EVIDENCE_SCOPE = "isolated_build_not_post_deploy_or_pc24x7"
ARTIFACTS = (
    "Gemfile.lock",
    "config/database.yml",
    "lib/redmine/version.rb",
    "public/reqsys-e2e/evidence.json",
)
MANIFEST_PATH = "public/reqsys-e2e/release-manifest.json"
RENDER_KEYS = (
    "RENDER", "RENDER_SERVICE_ID", "RENDER_GIT_COMMIT",
    "RENDER_GIT_BRANCH", "RENDER_GIT_REPO_SLUG",
)


class IdentityError(ValueError):
    """Erro estável: não inclui ambiente, segredo, caminho ou saída de Git."""


def _sha(value: object, length: int = 40) -> str:
    if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{" + str(length) + "}", value):
        raise IdentityError("RELEASE_SHA_INVALID")
    return value


def _root(value: Path) -> Path:
    root = Path(value)
    if not root.is_absolute() or not root.is_dir() or root.resolve() != root:
        raise IdentityError("RELEASE_ROOT_INVALID")
    return root


def _bytes(root: Path, relative: str) -> bytes:
    parts = relative.split("/")
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise IdentityError("RELEASE_PATH_INVALID")
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise IdentityError("RELEASE_SYMLINK_REJECTED")
    try:
        if not path.is_file() or path.stat().st_size > 5_000_000:
            raise IdentityError("RELEASE_FILE_INVALID")
        return path.read_bytes()
    except OSError:
        raise IdentityError("RELEASE_FILE_UNAVAILABLE") from None


def _git(root: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise IdentityError("RELEASE_GIT_UNAVAILABLE") from None
    if result.returncode or len(result.stdout) > 2_000_000:
        raise IdentityError("RELEASE_GIT_FAILED")
    return result.stdout


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _json(raw: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise IdentityError("RELEASE_JSON_DUPLICATE_KEY")
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError):
        raise IdentityError("RELEASE_JSON_INVALID") from None
    if not isinstance(value, dict):
        raise IdentityError("RELEASE_JSON_INVALID")
    return value


def validate_identity(identity: object, expected_sha: str) -> dict:
    _sha(expected_sha)
    keys = {
        "schema_version", "repository", "source_sha", "source_runtime_sha256",
        "provenance_method", "scope",
    }
    if not isinstance(identity, dict) or set(identity) != keys:
        raise IdentityError("RELEASE_IDENTITY_INVALID")
    if type(identity["schema_version"]) is not int or identity["schema_version"] != 1:
        raise IdentityError("RELEASE_SCHEMA_INVALID")
    if identity["repository"] != REPOSITORY or identity["scope"] != SOURCE_SCOPE:
        raise IdentityError("RELEASE_SOURCE_SCOPE_INVALID")
    if identity["provenance_method"] not in ("render_git_checkout", "github_hosted_verified_copy"):
        raise IdentityError("RELEASE_PROVENANCE_INVALID")
    if _sha(identity["source_sha"]) != expected_sha:
        raise IdentityError("RELEASE_SOURCE_SHA_MISMATCH")
    _sha(identity["source_runtime_sha256"], 64)
    return identity


def capture_source_identity(build_root: Path, env: dict[str, str]) -> dict:
    """Compara TODOS os arquivos rastreados de render_runtime com os blobs Git."""
    build_root = _root(build_root)
    if any(key in env for key in RENDER_KEYS):
        if (
            env.get("RENDER") != "true"
            or env.get("RENDER_SERVICE_ID") != SERVICE_ID
            or env.get("RENDER_GIT_REPO_SLUG") != REPOSITORY
            or env.get("RENDER_GIT_BRANCH") != BRANCH
        ):
            raise IdentityError("RELEASE_RENDER_CONTEXT_INVALID")
        expected_sha = _sha(env.get("RENDER_GIT_COMMIT"))
        source_root = build_root
        method = "render_git_checkout"
    else:
        if (
            env.get("GITHUB_ACTIONS") != "true"
            or env.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or env.get("GITHUB_REPOSITORY") != REPOSITORY
            or env.get("GITHUB_REF") != "refs/heads/" + BRANCH
            or not env.get("GITHUB_WORKSPACE")
        ):
            raise IdentityError("RELEASE_CI_CONTEXT_INVALID")
        expected_sha = _sha(env.get("GITHUB_SHA"))
        source_root = _root(Path(env["GITHUB_WORKSPACE"]))
        method = "github_hosted_verified_copy"
    try:
        head = _git(source_root, "rev-parse", "--verify", "HEAD").decode().strip()
        top = _git(source_root, "rev-parse", "--show-toplevel").decode().strip()
    except UnicodeError:
        raise IdentityError("RELEASE_GIT_RESPONSE_INVALID") from None
    if head != expected_sha or Path(top) != source_root:
        raise IdentityError("RELEASE_CHECKOUT_MISMATCH")
    entries = _git(source_root, "ls-tree", "-rz", "--full-tree", expected_sha, "--", "render_runtime")
    hashes = {}
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        try:
            header, path = entry.decode("utf-8").split("\t", 1)
            mode, kind, blob = header.split(" ")
        except (ValueError, UnicodeError):
            raise IdentityError("RELEASE_TREE_INVALID") from None
        if mode not in ("100644", "100755") or kind != "blob":
            raise IdentityError("RELEASE_TREE_TYPE_INVALID")
        if not path.startswith("render_runtime/") or path in hashes:
            raise IdentityError("RELEASE_TREE_PATH_INVALID")
        raw = _bytes(build_root, path)
        actual_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if actual_blob != _sha(blob):
            raise IdentityError("RELEASE_SNAPSHOT_MISMATCH")
        hashes[path] = hashlib.sha256(raw).hexdigest()
    if not {"render_runtime/build_redmine_6_1_4.sh", "render_runtime/release_identity.py"} <= set(hashes):
        raise IdentityError("RELEASE_SOURCE_INCOMPLETE")
    # Untracked runtime inputs can change imports. Builds disable bytecode writes.
    observed_paths = set()
    runtime_sources = build_root / "render_runtime"
    for path in runtime_sources.rglob("*"):
        if path.is_symlink():
            raise IdentityError("RELEASE_SYMLINK_REJECTED")
        if path.is_file():
            relative = path.relative_to(build_root).as_posix()
            observed_paths.add(relative)
    if observed_paths != set(hashes):
        raise IdentityError("RELEASE_UNTRACKED_SOURCE")
    identity = {
        "schema_version": 1,
        "repository": REPOSITORY,
        "source_sha": expected_sha,
        "source_runtime_sha256": hashlib.sha256(_json_bytes(hashes)).hexdigest(),
        "provenance_method": method,
        "scope": SOURCE_SCOPE,
    }
    return validate_identity(identity, expected_sha)


def _manifest(runtime_root: Path, identity: dict) -> dict:
    if not isinstance(identity, dict):
        raise IdentityError("RELEASE_IDENTITY_INVALID")
    validate_identity(identity, identity.get("source_sha", ""))
    artifacts = {path: hashlib.sha256(_bytes(runtime_root, path)).hexdigest() for path in ARTIFACTS}
    proof = _json(_bytes(runtime_root, ARTIFACTS[-1]))
    if (
        proof.get("status") != "passed"
        or proof.get("secret_values_in_evidence") is not False
        or proof.get("evidence_scope") != EVIDENCE_SCOPE
        or proof.get("redmine_repo_sha") != identity["source_sha"]
        or proof.get("source_identity") != identity
    ):
        raise IdentityError("RELEASE_EVIDENCE_IDENTITY_MISMATCH")
    redmine = proof.get("redmine")
    harness = proof.get("test_harness")
    if (
        not isinstance(redmine, dict)
        or redmine.get("version") not in ("6.1.5", "6.1.5.stable")
        or not isinstance(harness, dict)
        or set(harness) != {"source_sha", "blob_sha"}
    ):
        raise IdentityError("RELEASE_COMPONENT_IDENTITY_INVALID")
    _sha(proof.get("reqsys_sha"))
    for value in harness.values():
        _sha(value)
    return {
        "schema_version": 1,
        "source_identity": identity,
        "redmine_version": redmine["version"],
        "reqsys_sha": proof["reqsys_sha"],
        "test_harness": harness,
        "evidence_scope": EVIDENCE_SCOPE,
        "artifacts_sha256": artifacts,
    }


def verify_manifest(runtime_root: Path, expected_sha: str) -> dict:
    runtime_root = _root(runtime_root)
    manifest = _json(_bytes(runtime_root, MANIFEST_PATH))
    identity = validate_identity(manifest.get("source_identity"), expected_sha)
    if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise IdentityError("RELEASE_SCHEMA_INVALID")
    if manifest != _manifest(runtime_root, identity):
        raise IdentityError("RELEASE_MANIFEST_MISMATCH")
    return manifest


def write_manifest(runtime_root: Path, identity: dict) -> dict:
    runtime_root = _root(runtime_root)
    payload = _manifest(runtime_root, identity)
    path = runtime_root / MANIFEST_PATH
    if path.is_symlink():
        raise IdentityError("RELEASE_SYMLINK_REJECTED")
    raw = _json_bytes(payload)
    try:
        with path.open("xb") as stream:
            stream.write(raw)
    except FileExistsError:
        raise IdentityError("RELEASE_MANIFEST_EXISTS_PRESERVED") from None
    except OSError:
        raise IdentityError("RELEASE_MANIFEST_WRITE_FAILED") from None
    if _bytes(runtime_root, MANIFEST_PATH) != raw:
        raise IdentityError("RELEASE_MANIFEST_READBACK_FAILED")
    return verify_manifest(runtime_root, identity["source_sha"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("capture", "publish", "verify"))
    parser.add_argument("--expected-sha")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    try:
        if args.action == "capture":
            payload = capture_source_identity(root, dict(os.environ))
        elif args.action == "publish":
            identity = _json(os.environ.get("REQSYS_REDMINE_SOURCE_IDENTITY", "").encode())
            # Recheck tracked inputs after the build; changes cannot inherit the
            # preflight identity. This reads source files, never the live service.
            if identity != capture_source_identity(root, dict(os.environ)):
                raise IdentityError("RELEASE_SOURCE_CHANGED_DURING_BUILD")
            payload = write_manifest(root / ".runtime/redmine-6.1.5", identity)
        else:
            payload = verify_manifest(root / ".runtime/redmine-6.1.5", args.expected_sha)
        print(json.dumps(payload, sort_keys=True))
    except (IdentityError, OSError) as exc:
        message = str(exc) if isinstance(exc, IdentityError) else "RELEASE_IO_FAILED"
        print(message, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
