"""Prova de proveniência com Git real e artefatos fictícios, sem deploy ou Rails.

Os arquivos de runtime deste teste são dummies: não representam instalação,
credenciais, dados, E2E real do Redmine ou autorização para publicar um serviço.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from render_runtime import release_identity as target


REPOSITORY = "ericson-j-santos/redmine"
BRANCH = "dev/reqsys-e2e-redmine-6.1.4-20260928"
SERVICE_ID = "srv-dathlk2d0e5s73c5722g"
MANIFEST_PATH = "public/reqsys-e2e/release-manifest.json"
EVIDENCE_PATH = "public/reqsys-e2e/evidence.json"
ARTIFACT_PATHS = (
    "Gemfile.lock",
    "config/database.yml",
    "lib/redmine/version.rb",
    EVIDENCE_PATH,
)
SOURCE_PATHS = (
    "render_runtime/build_redmine_6_1_4.sh",
    "render_runtime/release_identity.py",
    "render_runtime/fixture-note.txt",
)


class ReleaseIdentityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="release-identity-fixture-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.source = self.base / "source"
        self.source.mkdir()
        self.git_env = {
            key: value for key, value in os.environ.items()
            if not key.startswith("GIT_")
        }
        self.git_env.update({
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_AUTHOR_NAME": "Release Identity Fixture",
            "GIT_AUTHOR_EMAIL": "release-fixture@example.invalid",
            "GIT_COMMITTER_NAME": "Release Identity Fixture",
            "GIT_COMMITTER_EMAIL": "release-fixture@example.invalid",
            "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
        })
        self.git("init", "--object-format=sha1", "--initial-branch=fixture")
        files = {
            SOURCE_PATHS[0]: b"#!/bin/sh\n# Dummy build source; never executed.\n",
            SOURCE_PATHS[1]: Path(target.__file__).read_bytes(),
            SOURCE_PATHS[2]: "Dummy source fixture: acentuação.\n".encode("utf-8"),
        }
        for relative, raw in files.items():
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        self.git("add", "--", "render_runtime")
        self.git("commit", "-m", "Record isolated fixture source")
        self.sha = self.git("rev-parse", "HEAD").decode("ascii").strip()

    def git(self, *args, input_bytes=None):
        return subprocess.run(
            [
                "git", "-C", str(self.source),
                "-c", "commit.gpgsign=false",
                "-c", "core.hooksPath=" + os.devnull,
                *args,
            ],
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.git_env,
            check=True,
            timeout=15,
        ).stdout

    def render_env(self):
        return {
            "RENDER": "true",
            "RENDER_SERVICE_ID": SERVICE_ID,
            "RENDER_GIT_COMMIT": self.sha,
            "RENDER_GIT_BRANCH": BRANCH,
            "RENDER_GIT_REPO_SLUG": REPOSITORY,
        }

    def ci_env(self):
        return {
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "push",
            "RUNNER_ENVIRONMENT": "github-hosted",
            "GITHUB_REPOSITORY": REPOSITORY,
            "GITHUB_REF": "refs/heads/" + BRANCH,
            "GITHUB_WORKSPACE": str(self.source),
            "GITHUB_SHA": self.sha,
        }

    def pr_env(self):
        return {
            **self.ci_env(),
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_REF": "refs/pull/17/merge",
            "GITHUB_BASE_REF": BRANCH,
            "GITHUB_HEAD_REF": "fix/native-backup",
        }

    def copy_source(self):
        copied = self.base / "copied-build"
        shutil.copytree(self.source / "render_runtime", copied / "render_runtime")
        return copied

    def identity(self):
        return target.capture_source_identity(self.source, self.render_env())

    def assert_git_bytes(self, root):
        # Git itself supplies the expected bytes and computes object identity.
        # Do not reproduce release_identity's fingerprint serialization here.
        for relative in SOURCE_PATHS:
            with self.subTest(source_file=relative):
                observed = (root / relative).read_bytes()
                committed = self.git("cat-file", "blob", "HEAD:" + relative)
                self.assertEqual(observed, committed)
                committed_oid = self.git("rev-parse", "HEAD:" + relative).strip()
                observed_oid = self.git("hash-object", "--stdin", input_bytes=observed).strip()
                self.assertEqual(observed_oid, committed_oid)

    def runtime_fixture(self, identity, root=None):
        runtime = root or self.base / "dummy-runtime"
        fixtures = {
            "Gemfile.lock": b"# Dummy artifact: no installed gems.\n",
            "config/database.yml": b"# Dummy artifact: no database connection.\nfixture_only: true\n",
            "lib/redmine/version.rb": b"# Dummy artifact: not a loaded Redmine runtime.\n",
        }
        for relative, raw in fixtures.items():
            path = runtime / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        proof = {
            "fixture_only": True,
            "status": "passed",
            "secret_values_in_evidence": False,
            "evidence_scope": "isolated_build_not_post_deploy_or_pc24x7",
            "redmine_repo_sha": identity["source_sha"],
            "source_identity": deepcopy(identity),
            "redmine": {"version": "6.1.5.stable"},
            "reqsys_sha": "a" * 40,
            "test_harness": {"source_sha": "b" * 40, "blob_sha": "c" * 40},
        }
        self.write_json(runtime / EVIDENCE_PATH, proof)
        return runtime, proof

    @staticmethod
    def write_json(path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def cli(self, action, env, *args):
        environment = dict(self.git_env)
        for key in tuple(environment):
            if key.startswith(("GITHUB_", "RENDER_")) or key in (
                "RENDER", "RUNNER_ENVIRONMENT", "PYTHONPATH",
                "REQSYS_REDMINE_SOURCE_IDENTITY",
            ):
                environment.pop(key)
        environment.update(env)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [
                sys.executable, "-B",
                str(self.source / "render_runtime/release_identity.py"),
                action, *args,
            ],
            cwd=self.base,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )

    def test_render_capture_matches_real_git_and_replays(self):
        identity = self.identity()
        self.assert_git_bytes(self.source)
        self.assertEqual(identity["source_sha"], self.git("rev-parse", "HEAD").decode().strip())
        self.assertEqual(identity["repository"], REPOSITORY)
        self.assertEqual(identity["provenance_method"], "render_git_checkout")
        self.assertEqual(identity["scope"], "tracked_build_source_not_deployment_authorization")
        self.assertEqual(identity["schema_version"], 1)
        self.assertRegex(identity["source_runtime_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(self.identity(), identity)
        self.assertEqual(self.git("status", "--porcelain", "--", "render_runtime"), b"")

    def test_ci_copy_without_git_has_same_source_identity(self):
        original = self.identity()
        copied = self.copy_source()
        self.assertFalse((copied / ".git").exists())
        self.assert_git_bytes(copied)
        identity = target.capture_source_identity(copied, self.ci_env())
        self.assertEqual(identity["provenance_method"], "github_hosted_verified_copy")
        self.assertEqual(
            {key: value for key, value in identity.items() if key != "provenance_method"},
            {key: value for key, value in original.items() if key != "provenance_method"},
        )
        self.assertEqual(target.capture_source_identity(copied, self.ci_env()), identity)

    def test_pull_request_requires_exact_dev_base_merge_ref_and_checkout_sha(self):
        copied = self.copy_source()
        identity = target.capture_source_identity(copied, self.pr_env())
        self.assertEqual(identity["source_sha"], self.sha)
        self.assertEqual(identity["provenance_method"], "github_hosted_verified_copy")
        for field, bad in (
            ("GITHUB_EVENT_NAME", "pull_request_target"),
            ("GITHUB_BASE_REF", "main"),
            ("GITHUB_BASE_REF", ""),
            ("GITHUB_REF", "refs/heads/" + BRANCH),
            ("GITHUB_REF", "refs/pull/0/merge"),
            ("GITHUB_REF", "refs/pull/17/head"),
            ("GITHUB_HEAD_REF", ""),
            ("GITHUB_HEAD_REF", "bad\nhead"),
        ):
            with self.subTest(field=field, bad=bad):
                with self.assertRaisesRegex(
                    target.IdentityError,
                    "^RELEASE_CI_CONTEXT_INVALID$",
                ):
                    target.capture_source_identity(copied, {**self.pr_env(), field: bad})
        with self.assertRaisesRegex(target.IdentityError, "^RELEASE_CHECKOUT_MISMATCH$"):
            target.capture_source_identity(
                copied,
                {**self.pr_env(), "GITHUB_SHA": "0" * 40},
            )
        for field in ("GITHUB_BASE_REF", "GITHUB_HEAD_REF"):
            with self.subTest(push_hybrid_field=field), self.assertRaisesRegex(
                target.IdentityError,
                "^RELEASE_CI_CONTEXT_INVALID$",
            ):
                target.capture_source_identity(
                    copied,
                    {**self.ci_env(), field: "unexpected-pr-metadata"},
                )
        dispatch = {**self.ci_env(), "GITHUB_EVENT_NAME": "workflow_dispatch"}
        self.assertEqual(target.capture_source_identity(copied, dispatch), identity)

    def test_workflows_propagate_event_and_execute_pull_request_regression(self):
        root = Path(__file__).resolve().parents[2]
        lint = (root / ".github/workflows/linters.yml").read_text(encoding="utf-8")
        native = (root / ".github/workflows/native-linux-portability.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn('"GITHUB_EVENT_NAME": os.environ["GITHUB_EVENT_NAME"]', lint)
        self.assertIn(
            "python3 -B -m unittest render_runtime.tests.test_release_identity -v",
            native,
        )
        py_compile_block = native.split("python3 -B -m py_compile", 1)[1].split(
            "python3 -B -m unittest", 1
        )[0]
        self.assertNotIn("render_runtime/", py_compile_block)

    def test_partial_or_wrong_render_context_cannot_fall_back_to_ci(self):
        for field, bad in (
            ("RENDER", "false"),
            ("RENDER_SERVICE_ID", "fixture-wrong-service"),
            ("RENDER_GIT_BRANCH", "main"),
            ("RENDER_GIT_REPO_SLUG", "fixture-do-not-echo"),
        ):
            with self.subTest(field=field):
                env = {**self.ci_env(), **self.render_env(), field: bad}
                with self.assertRaisesRegex(target.IdentityError, "^RELEASE_RENDER_CONTEXT_INVALID$") as error:
                    target.capture_source_identity(self.source, env)
                self.assertNotIn(bad, str(error.exception))
        with self.assertRaisesRegex(target.IdentityError, "RENDER_CONTEXT_INVALID"):
            target.capture_source_identity(self.source, {**self.ci_env(), "RENDER": "true"})

    def test_ci_context_requires_hosted_runner_repository_branch_and_workspace(self):
        for field, bad in (
            ("GITHUB_ACTIONS", "false"),
            ("GITHUB_EVENT_NAME", "schedule"),
            ("RUNNER_ENVIRONMENT", "self-hosted"),
            ("GITHUB_REPOSITORY", "fixture/wrong-repository"),
            ("GITHUB_REF", "refs/heads/main"),
            ("GITHUB_WORKSPACE", ""),
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(target.IdentityError, "^RELEASE_CI_CONTEXT_INVALID$"):
                    target.capture_source_identity(self.source, {**self.ci_env(), field: bad})
        with self.assertRaisesRegex(target.IdentityError, "CI_CONTEXT_INVALID"):
            target.capture_source_identity(self.source, {})

    def test_sha_syntax_and_actual_checkout_must_agree(self):
        for bad in ("", "1234567", "A" * 40, "g" * 40, None):
            for context, field in ((self.render_env(), "RENDER_GIT_COMMIT"),
                                   (self.ci_env(), "GITHUB_SHA")):
                with self.subTest(value=bad, field=field):
                    with self.assertRaisesRegex(target.IdentityError, "^RELEASE_SHA_INVALID$"):
                        target.capture_source_identity(self.source, {**context, field: bad})
        for context, field in ((self.render_env(), "RENDER_GIT_COMMIT"),
                               (self.ci_env(), "GITHUB_SHA")):
            with self.assertRaisesRegex(target.IdentityError, "^RELEASE_CHECKOUT_MISMATCH$"):
                target.capture_source_identity(self.source, {**context, field: "0" * 40})

    def test_root_must_be_absolute_real_and_the_git_toplevel(self):
        alias = self.base / "source-alias"
        alias.symlink_to(self.source, target_is_directory=True)
        for root in (Path("relative-fixture"), alias, self.base / "absent"):
            with self.subTest(root=root.name):
                with self.assertRaisesRegex(target.IdentityError, "^RELEASE_ROOT_INVALID$"):
                    target.capture_source_identity(root, self.render_env())
        nested = self.source / "nested"
        nested.mkdir()
        with self.assertRaisesRegex(target.IdentityError, "^RELEASE_CHECKOUT_MISMATCH$"):
            target.capture_source_identity(nested, self.render_env())
        with self.assertRaisesRegex(target.IdentityError, "^RELEASE_ROOT_INVALID$"):
            target.capture_source_identity(self.source, {**self.ci_env(), "GITHUB_WORKSPACE": str(alias)})

    def test_tracked_tamper_is_detected_and_restoration_replays(self):
        before = self.identity()
        path = self.source / SOURCE_PATHS[2]
        original = self.git("cat-file", "blob", "HEAD:" + SOURCE_PATHS[2])
        try:
            path.write_bytes(original + b"uncommitted fixture mutation\n")
            with self.assertRaisesRegex(target.IdentityError, "^RELEASE_SNAPSHOT_MISMATCH$"):
                self.identity()
        finally:
            path.write_bytes(original)
        self.assert_git_bytes(self.source)
        self.assertEqual(self.identity(), before)

    def test_missing_and_untracked_copied_inputs_are_rejected_then_restored(self):
        copied = self.copy_source()
        env = self.ci_env()
        before = target.capture_source_identity(copied, env)
        path = copied / SOURCE_PATHS[2]
        original = path.read_bytes()
        path.unlink()
        try:
            with self.assertRaisesRegex(target.IdentityError, "^RELEASE_FILE_INVALID$"):
                target.capture_source_identity(copied, env)
        finally:
            path.write_bytes(original)
        for relative in ("render_runtime/untracked.py", "render_runtime/__pycache__/fixture.pyc"):
            extra = copied / relative
            extra.parent.mkdir(parents=True, exist_ok=True)
            extra.write_bytes(b"dummy untracked import input")
            try:
                with self.subTest(relative=relative):
                    with self.assertRaisesRegex(target.IdentityError, "^RELEASE_UNTRACKED_SOURCE$"):
                        target.capture_source_identity(copied, env)
            finally:
                extra.unlink()
        self.assert_git_bytes(copied)
        self.assertEqual(target.capture_source_identity(copied, env), before)

    def test_source_file_parent_and_untracked_symlinks_are_rejected(self):
        copied = self.copy_source()
        outside = self.base / "dummy-outside"
        outside.write_bytes(b"dummy symlink target")
        path = copied / SOURCE_PATHS[2]
        original = path.read_bytes()
        path.unlink()
        path.symlink_to(outside)
        try:
            with self.assertRaisesRegex(target.IdentityError, "^RELEASE_SYMLINK_REJECTED$"):
                target.capture_source_identity(copied, self.ci_env())
        finally:
            path.unlink()
            path.write_bytes(original)
        extra = copied / "render_runtime/untracked-link"
        extra.symlink_to(outside)
        try:
            with self.assertRaisesRegex(target.IdentityError, "^RELEASE_SYMLINK_REJECTED$"):
                target.capture_source_identity(copied, self.ci_env())
        finally:
            extra.unlink()
        directory = copied / "render_runtime"
        held = copied / "held-runtime"
        directory.rename(held)
        directory.symlink_to(held, target_is_directory=True)
        try:
            with self.assertRaisesRegex(target.IdentityError, "^RELEASE_SYMLINK_REJECTED$"):
                target.capture_source_identity(copied, self.ci_env())
        finally:
            directory.unlink()
            held.rename(directory)
        self.assert_git_bytes(copied)
        self.assertEqual(outside.read_bytes(), b"dummy symlink target")

    def test_git_tree_requires_mandatory_files_and_regular_blob_modes(self):
        initial_sha = self.sha
        self.git("rm", "--", SOURCE_PATHS[0])
        self.git("commit", "-m", "Remove required dummy source")
        self.sha = self.git("rev-parse", "HEAD").decode().strip()
        with self.assertRaisesRegex(target.IdentityError, "^RELEASE_SOURCE_INCOMPLETE$"):
            self.identity()
        # This reset is confined to the newly created disposable fixture repo.
        self.git("reset", "--hard", initial_sha)
        self.sha = initial_sha
        self.assert_git_bytes(self.source)
        link = self.source / "render_runtime/committed-link"
        link.symlink_to("fixture-note.txt")
        self.git("add", "--", "render_runtime/committed-link")
        self.git("commit", "-m", "Track a forbidden symlink fixture")
        self.sha = self.git("rev-parse", "HEAD").decode().strip()
        with self.assertRaisesRegex(target.IdentityError, "^RELEASE_TREE_TYPE_INVALID$"):
            self.identity()

    def test_head_advance_cannot_replace_the_observed_commit_blobs(self):
        before = self.identity()
        copied = self.copy_source()
        captured_sha = self.sha
        env = self.ci_env()
        real_run = subprocess.run
        advanced = []

        def advance_before_tree(command, *args, **kwargs):
            if command[0] == "git" and "ls-tree" in command and not advanced:
                advanced.append(True)
                note = self.source / SOURCE_PATHS[2]
                note.write_bytes(note.read_bytes() + b"new committed fixture revision\\n")
                self.git("add", "--", SOURCE_PATHS[2])
                self.git("commit", "-m", "Advance HEAD after the initial observation")
            return real_run(command, *args, **kwargs)

        # Only the timing boundary is injected. All Git reads, writes and commits
        # remain real; the copied build retains the first commit's actual bytes.
        with patch.object(subprocess, "run", advance_before_tree):
            pinned = target.capture_source_identity(copied, env)
        self.assertEqual(advanced, [True])
        self.assertEqual(pinned["source_sha"], captured_sha)
        self.assertEqual(pinned["source_runtime_sha256"], before["source_runtime_sha256"])
        for relative in SOURCE_PATHS:
            self.assertEqual(
                (copied / relative).read_bytes(),
                self.git("cat-file", "blob", captured_sha + ":" + relative),
            )
        self.sha = self.git("rev-parse", "HEAD").decode().strip()
        after = self.identity()
        self.assert_git_bytes(self.source)
        self.assertNotEqual(after["source_sha"], before["source_sha"])
        self.assertNotEqual(after["source_runtime_sha256"], before["source_runtime_sha256"])
        self.assertEqual(after["source_sha"], self.sha)
        self.assertEqual(self.identity(), after)

    def test_manifest_hashes_match_independent_reads_and_verify_replays(self):
        identity = self.identity()
        runtime, proof = self.runtime_fixture(identity)
        expected = {
            relative: hashlib.sha256((runtime / relative).read_bytes()).hexdigest()
            for relative in ARTIFACT_PATHS
        }
        result = target.write_manifest(runtime, identity)
        manifest_path = runtime / MANIFEST_PATH
        persisted = json.loads(manifest_path.read_bytes())
        self.assertEqual(persisted, result)
        self.assertEqual(persisted["artifacts_sha256"], expected)
        self.assertEqual(persisted["source_identity"], identity)
        self.assertEqual(persisted["reqsys_sha"], proof["reqsys_sha"])
        self.assertEqual(persisted["test_harness"], proof["test_harness"])
        self.assertEqual(persisted["redmine_version"], "6.1.5.stable")
        before = manifest_path.read_bytes()
        for _ in range(2):
            self.assertEqual(target.verify_manifest(runtime, self.sha), persisted)
        self.assertEqual(manifest_path.read_bytes(), before)

    def test_identity_schema_scope_and_digest_fail_closed(self):
        valid = self.identity()
        candidates = [None, [], {}, {**valid, "extra": "fixture"}]
        for field, bad in (
            ("schema_version", True),
            ("repository", "fixture/wrong"),
            ("scope", "deployment_authorized"),
            ("provenance_method", "trust_environment_without_git"),
            ("source_runtime_sha256", "0" * 63),
            ("source_sha", "0" * 40),
        ):
            candidates.append({**valid, field: bad})
        for candidate in candidates:
            with self.subTest(candidate_type=type(candidate).__name__):
                with self.assertRaises(target.IdentityError):
                    target.validate_identity(candidate, self.sha)
        self.assertEqual(target.validate_identity(valid, self.sha), valid)

    def test_invalid_evidence_never_creates_a_manifest(self):
        identity = self.identity()
        runtime, valid = self.runtime_fixture(identity)
        candidates = []
        for field, bad in (
            ("status", "failed"),
            ("secret_values_in_evidence", True),
            ("evidence_scope", "published_service_validated"),
            ("redmine_repo_sha", "0" * 40),
            ("source_identity", {**identity, "source_runtime_sha256": "0" * 64}),
            ("reqsys_sha", "short"),
            ("redmine", {"version": "6.1.4"}),
            ("test_harness", {"source_sha": "b" * 40}),
            ("test_harness", {"source_sha": "bad", "blob_sha": "c" * 40}),
        ):
            candidates.append((field, {**deepcopy(valid), field: bad}))
        for field, proof in candidates:
            with self.subTest(field=field):
                self.write_json(runtime / EVIDENCE_PATH, proof)
                supplied = (runtime / EVIDENCE_PATH).read_bytes()
                with self.assertRaises(target.IdentityError):
                    target.write_manifest(runtime, identity)
                self.assertFalse((runtime / MANIFEST_PATH).exists())
                self.assertEqual((runtime / EVIDENCE_PATH).read_bytes(), supplied)
        self.write_json(runtime / EVIDENCE_PATH, valid)
        result = target.write_manifest(runtime, identity)
        self.assertEqual(target.verify_manifest(runtime, self.sha), result)

    def test_manifest_tamper_is_detected_and_original_bytes_restore(self):
        identity = self.identity()
        runtime, _ = self.runtime_fixture(identity)
        original = target.write_manifest(runtime, identity)
        path = runtime / MANIFEST_PATH
        original_bytes = path.read_bytes()
        cases = (
            {"schema_version": True},
            {"evidence_scope": "deployment_authorized"},
            {"reqsys_sha": "d" * 40},
            {"artifacts_sha256": {}},
            {"source_identity": {**identity, "source_sha": "0" * 40}},
            {"unexpected": "fixture"},
        )
        for mutation in cases:
            with self.subTest(fields=tuple(mutation)):
                self.write_json(path, {**deepcopy(original), **mutation})
                try:
                    with self.assertRaises(target.IdentityError):
                        target.verify_manifest(runtime, self.sha)
                finally:
                    path.write_bytes(original_bytes)
                self.assertEqual(target.verify_manifest(runtime, self.sha), original)
        with self.assertRaisesRegex(target.IdentityError, "^RELEASE_SOURCE_SHA_MISMATCH$"):
            target.verify_manifest(runtime, "0" * 40)
        self.assertEqual(path.read_bytes(), original_bytes)

    def test_runtime_artifact_tamper_missing_and_symlink_require_restoration(self):
        identity = self.identity()
        runtime, _ = self.runtime_fixture(identity)
        manifest = target.write_manifest(runtime, identity)
        outside = self.base / "dummy-artifact-link-target"
        outside.write_bytes(b"dummy outside artifact")
        for relative in ARTIFACT_PATHS:
            path = runtime / relative
            original = path.read_bytes()
            for mode in ("tamper", "missing", "symlink"):
                with self.subTest(artifact=relative, mode=mode):
                    if mode == "tamper":
                        path.write_bytes(original + b"fixture corruption")
                    else:
                        path.unlink()
                        if mode == "symlink":
                            path.symlink_to(outside)
                    try:
                        with self.assertRaises(target.IdentityError):
                            target.verify_manifest(runtime, self.sha)
                    finally:
                        if path.is_symlink():
                            path.unlink()
                        path.write_bytes(original)
                    self.assertEqual(target.verify_manifest(runtime, self.sha), manifest)
        self.assertEqual(outside.read_bytes(), b"dummy outside artifact")

    def test_invalid_or_duplicate_json_cannot_pass_manifest_verification(self):
        identity = self.identity()
        runtime, _ = self.runtime_fixture(identity)
        original = target.write_manifest(runtime, identity)
        path = runtime / MANIFEST_PATH
        original_bytes = path.read_bytes()
        duplicate = b'{"schema_version":1,"schema_version":1,' + original_bytes.lstrip()[1:]
        for raw in (b"", b"[1]", b"{", b"\xff", duplicate):
            with self.subTest(raw_length=len(raw)):
                path.write_bytes(raw)
                try:
                    with self.assertRaises(target.IdentityError):
                        target.verify_manifest(runtime, self.sha)
                finally:
                    path.write_bytes(original_bytes)
        proof_path = runtime / EVIDENCE_PATH
        proof_bytes = proof_path.read_bytes()
        proof_path.write_bytes(b'{"status":"passed","status":"passed",' + proof_bytes.lstrip()[1:])
        try:
            with self.assertRaises(target.IdentityError):
                target.verify_manifest(runtime, self.sha)
        finally:
            proof_path.write_bytes(proof_bytes)
        self.assertEqual(target.verify_manifest(runtime, self.sha), original)

    def test_exclusive_write_preserves_existing_manifest_and_symlink_target(self):
        identity = self.identity()
        runtime, _ = self.runtime_fixture(identity)
        manifest = target.write_manifest(runtime, identity)
        path = runtime / MANIFEST_PATH
        original = path.read_bytes()
        stat = path.stat()
        with self.assertRaisesRegex(target.IdentityError, "^RELEASE_MANIFEST_EXISTS_PRESERVED$"):
            target.write_manifest(runtime, identity)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(path.stat().st_mtime_ns, stat.st_mtime_ns)
        outside = self.base / "existing-manifest-target"
        outside.write_bytes(original)
        path.unlink()
        path.symlink_to(outside)
        try:
            with self.assertRaisesRegex(target.IdentityError, "^RELEASE_SYMLINK_REJECTED$"):
                target.write_manifest(runtime, identity)
            self.assertEqual(outside.read_bytes(), original)
        finally:
            path.unlink()
            path.write_bytes(original)
        self.assertEqual(target.verify_manifest(runtime, self.sha), manifest)

    def test_short_write_false_success_is_detected_by_readback_and_recovered(self):
        identity = self.identity()
        runtime, _ = self.runtime_fixture(identity)
        manifest_path = runtime / MANIFEST_PATH
        real_open = Path.open

        class ShortWriter:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                return self

            def write(self, raw):
                self.stream.write(raw[:-7])
                return len(raw)  # Deliberate false success from the writer.

            def __exit__(self, *exc):
                self.stream.close()
                return False

        def faulty_open(path, mode="r", *args, **kwargs):
            stream = real_open(path, mode, *args, **kwargs)
            if path == manifest_path and mode == "xb":
                return ShortWriter(stream)
            return stream

        with patch.object(Path, "open", faulty_open):
            with self.assertRaisesRegex(target.IdentityError, "^RELEASE_MANIFEST_READBACK_FAILED$"):
                target.write_manifest(runtime, identity)
        self.assertTrue(manifest_path.is_file())
        with self.assertRaises(target.IdentityError):
            target.verify_manifest(runtime, self.sha)
        # Remove only the intentionally truncated disposable fixture output.
        manifest_path.unlink()
        good = target.write_manifest(runtime, identity)
        self.assertEqual(json.loads(manifest_path.read_bytes()), good)
        self.assertEqual(target.verify_manifest(runtime, self.sha), good)

    def test_real_cli_capture_publish_verify_and_source_change_guard(self):
        env = self.render_env()
        captured = self.cli("capture", env)
        self.assertEqual(captured.returncode, 0, captured.stderr.decode())
        self.assertEqual(captured.stderr, b"")
        identity = json.loads(captured.stdout)
        self.assertEqual(identity, self.identity())
        runtime, _ = self.runtime_fixture(
            identity, self.source / ".runtime/redmine-6.1.5",
        )
        env["REQSYS_REDMINE_SOURCE_IDENTITY"] = json.dumps(identity)
        published = self.cli("publish", env)
        self.assertEqual(published.returncode, 0, published.stderr.decode())
        manifest = json.loads(published.stdout)
        original_bytes = (runtime / MANIFEST_PATH).read_bytes()
        verified = self.cli("verify", env, "--expected-sha", self.sha)
        self.assertEqual(verified.returncode, 0, verified.stderr.decode())
        self.assertEqual(json.loads(verified.stdout), manifest)
        note = self.source / SOURCE_PATHS[2]
        note.write_bytes(note.read_bytes() + b"new fixture commit during build\n")
        self.git("add", "--", SOURCE_PATHS[2])
        self.git("commit", "-m", "Change source after captured identity")
        self.sha = self.git("rev-parse", "HEAD").decode().strip()
        changed_env = {
            **env,
            "RENDER_GIT_COMMIT": self.sha,
            "UNTRUSTED_FIXTURE_VALUE": "fixture-do-not-echo",
        }
        rejected = self.cli("publish", changed_env)
        self.assertEqual(rejected.returncode, 2)
        self.assertEqual(rejected.stdout, b"")
        self.assertEqual(rejected.stderr.strip(), b"RELEASE_SOURCE_CHANGED_DURING_BUILD")
        self.assertEqual((runtime / MANIFEST_PATH).read_bytes(), original_bytes)
        self.assertEqual(json.loads(original_bytes), manifest)


if __name__ == "__main__":
    unittest.main()
