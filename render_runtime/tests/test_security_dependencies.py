"""Contratos locais da política; suites Ruby e lifecycle reais executam no build."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from render_runtime import security_dependencies as policy


class DependencyPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / "Gemfile"
        self.original = (Path(__file__).parent / "fixtures/redmine_6_1_5.Gemfile").read_bytes()
        self.target.write_bytes(self.original)

    def test_exact_upstream_fixture_and_three_line_change(self):
        self.assertEqual(policy.blob_sha(self.original), policy.UPSTREAM_BLOB)
        expected = self.original
        for name, version in policy.PINS.items():
            expected = expected.replace(
                f"gem '{name}', '{policy.OLD[name]}'".encode(),
                f"gem '{name}', '{version}'".encode())
        result = policy.hardened_gemfile(self.original)
        self.assertEqual(result, expected)
        self.assertEqual(sum(a != b for a, b in zip(
            result.splitlines(), self.original.splitlines())), 3)

    def test_positive_atomic_readback_and_replay_keep_inode_and_bytes(self):
        self.assertTrue(policy.apply_pins(self.target))
        before = self.target.read_bytes()
        info = self.target.stat()
        for _ in range(3):
            self.assertFalse(policy.apply_pins(self.target))
        self.assertEqual(before, self.target.read_bytes())
        self.assertEqual(info.st_ino, self.target.stat().st_ino)
        self.assertEqual(info.st_mtime_ns, self.target.stat().st_mtime_ns)
        self.assertEqual(list(self.root.iterdir()), [self.target])

    def test_unexpected_upstream_and_duplicate_declaration_fail_before_write(self):
        for change in (b"# changed\n", b"gem 'mail', '~> 2.8.1'\n"):
            with self.subTest(change=change):
                raw = self.original + change
                self.target.write_bytes(raw)
                with self.assertRaises(policy.DependencyPolicyError):
                    policy.apply_pins(self.target)
                self.assertEqual(self.target.read_bytes(), raw)

    def test_partial_patch_is_rejected(self):
        raw = self.original.replace(b"gem 'mail', '~> 2.8.1'", b"gem 'mail', '2.9.1'")
        with self.assertRaisesRegex(policy.DependencyPolicyError, "PARTIAL_PATCH"):
            policy.hardened_gemfile(raw)

    def test_unknown_version_and_downgrade_are_rejected(self):
        fixed = policy.hardened_gemfile(self.original)
        for version in ("2.8.1", "2.9.0", "9.0.0"):
            with self.subTest(version=version):
                with self.assertRaises(policy.DependencyPolicyError):
                    policy.hardened_gemfile(fixed.replace(b"'2.9.1'", repr(version).encode()))

    def test_exclusive_lock_blocks_concurrent_writer(self):
        lock = self.root / ".reqsys-dependency-pins.lock"
        lock.write_text("owned-by-another-worker", encoding="utf-8")
        with self.assertRaisesRegex(policy.DependencyPolicyError, "PATCH_BUSY"):
            policy.apply_pins(self.target)
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertEqual(lock.read_text(), "owned-by-another-worker")

    def test_symlink_and_hardlink_targets_are_preserved(self):
        link = self.root / "alias"
        link.symlink_to(self.target)
        with self.assertRaisesRegex(policy.DependencyPolicyError, "NOT_REGULAR"):
            policy.apply_pins(link)
        link.unlink()
        os.link(self.target, link)
        with self.assertRaisesRegex(policy.DependencyPolicyError, "NOT_REGULAR"):
            policy.apply_pins(self.target)
        self.assertEqual(self.target.read_bytes(), self.original)

    def test_replace_failure_preserves_original_and_cleans_only_own_temp(self):
        with patch.object(policy.os, "replace", side_effect=OSError("test-only")):
            with self.assertRaises(OSError):
                policy.apply_pins(self.target)
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertEqual(list(self.root.iterdir()), [self.target])

    def test_external_change_is_not_overwritten(self):
        real_fsync = policy.os.fsync
        def concurrent_write(fd):
            real_fsync(fd)
            self.target.write_bytes(b"changed-by-other-worker")
        with patch.object(policy.os, "fsync", side_effect=concurrent_write):
            with self.assertRaisesRegex(policy.DependencyPolicyError, "TARGET_CHANGED"):
                policy.apply_pins(self.target)
        self.assertEqual(self.target.read_bytes(), b"changed-by-other-worker")

    def test_missing_scope_blocks_cli_without_mutation(self):
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                policy.main(["patch"])
        self.assertEqual(error.exception.code, 2)
        self.assertEqual(self.target.read_bytes(), self.original)

    def test_missing_target_and_invalid_bytes_fail(self):
        for raw in ("not-bytes", b"x" * 16385, b""):
            with self.subTest(raw_type=type(raw).__name__):
                with self.assertRaises(policy.DependencyPolicyError):
                    policy.hardened_gemfile(raw)
        with self.assertRaises(FileNotFoundError):
            policy.apply_pins(self.root / "absent")

    def test_test_summary_requires_real_execution_and_zero_failures(self):
        good = "Finished\n10 runs, 25 assertions, 0 failures, 0 errors, 1 skips\n"
        self.assertEqual(policy.test_summary(good)["runs"], 10)
        for bad in ("success", "", good + good, "0 runs, 0 assertions, 0 failures, 0 errors, 0 skips",
                    "10 runs, 25 assertions, 0 failures, 0 errors, 10 skips",
                    "10 runs, 25 assertions, 1 failures, 0 errors, 0 skips",
                    "10 runs, 25 assertions, 0 failures, 1 errors, 0 skips"):
            with self.subTest(summary=bad):
                with self.assertRaises(policy.DependencyPolicyError):
                    policy.test_summary(bad)

    def prepare_proof_fixture(self):
        self.target.write_bytes(policy.hardened_gemfile(self.original))
        (self.root / "tmp").mkdir()
        (self.root / "tmp/reqsys-loaded-gems.json").write_text(json.dumps(policy.PINS))
        lock = "\n".join(f"    {name} ({version})" for name, version in policy.PINS.items())
        (self.root / "Gemfile.lock").write_text(lock)
        for name in ("attachment", "mailer"):
            (self.root / f"tmp/reqsys-{name}-compat.log").write_text(
                "10 runs, 25 assertions, 0 failures, 0 errors, 0 skips\n")

    def test_proof_requires_loaded_versions_lock_and_test_summaries(self):
        self.prepare_proof_fixture()
        proof = policy.verify_compatibility(self.root)
        self.assertEqual(proof["versions"], policy.PINS)
        self.assertEqual(proof["suites"]["attachment"]["runs"], 10)
        self.assertEqual(proof["lock_sha256"], policy.hashlib.sha256(
            (self.root / "Gemfile.lock").read_bytes()).hexdigest())

    def test_old_runtime_fails_new_proof_contract(self):
        self.prepare_proof_fixture()
        self.target.write_bytes(self.original)
        with self.assertRaisesRegex(policy.DependencyPolicyError, "PATCH_NOT_APPLIED"):
            policy.verify_compatibility(self.root)

    def test_wrong_loaded_version_fails(self):
        self.prepare_proof_fixture()
        loaded = dict(policy.PINS, sqlite3="2.5.0")
        (self.root / "tmp/reqsys-loaded-gems.json").write_text(json.dumps(loaded))
        with self.assertRaisesRegex(policy.DependencyPolicyError, "LOADED_VERSIONS_MISMATCH"):
            policy.verify_compatibility(self.root)

    def test_wrong_lock_platform_version_fails(self):
        self.prepare_proof_fixture()
        with (self.root / "Gemfile.lock").open("a") as output:
            output.write("\n    sqlite3 (2.5.0-x86_64-linux)\n")
        with self.assertRaisesRegex(policy.DependencyPolicyError, "LOCK_VERSIONS_MISMATCH"):
            policy.verify_compatibility(self.root)

    def test_runtime_paths_refuse_links(self):
        script = self.root / "render_runtime/security_dependencies.py"
        with patch.object(policy, "__file__", str(script)), patch.dict(
            os.environ, {"REQSYS_REDMINE_EPHEMERAL_E2E": "1"}, clear=True
        ):
            with self.assertRaisesRegex(policy.DependencyPolicyError, "RUNTIME_PATH_INVALID"):
                policy.runtime_root()
            (self.root / ".runtime").symlink_to(self.root, target_is_directory=True)
            with self.assertRaisesRegex(policy.DependencyPolicyError, "RUNTIME_PATH_INVALID"):
                policy.runtime_root()

    def test_build_keeps_lifecycle_and_audit_gates_and_separate_test_database(self):
        runtime = Path(__file__).resolve().parents[1]
        build = (runtime / "build_redmine_6_1_4.sh").read_text(encoding="utf-8")
        self.assertLess(build.index('runtime_safety.py" reserve'), build.index('security_dependencies.py" patch'))
        self.assertLess(build.index('security_dependencies.py" patch'), build.index("bundle lock"))
        self.assertLess(build.index("bundle audit check --update"), build.index('STAGE="legacy_start_compatibility"'))
        for name in ("attachment", "mailer"):
            self.assertIn(f"test/unit/{name}_test.rb", build)
            self.assertIn(f"tmp/reqsys-{name}-compat.log", build)
        self.assertIn("set -Eeuo pipefail", build)
        self.assertIn('REQSYS_SHA="9be16bfee3a3b8f9e3478e197e77d9231cdc4be6"', build)
        self.assertIn('HARNESS_SOURCE_SHA="b84576f76fad584bc420cb447d046aaafdc775ba"', build)
        self.assertIn('EXPECTED_SHA256="4b653d8863c012fdb226aedf6f8a18bdfa08d04625d15e8aafbbc3c4f6b70144"', build)
        self.assertNotIn("--ignore", build)
        config = (runtime / "database.yml").read_text()
        self.assertIn("reqsys_redmine_e2e.sqlite3", config)
        self.assertIn("reqsys_dependency_test.sqlite3", config)


if __name__ == "__main__":
    unittest.main()
