import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "native_runtime.py"
spec = importlib.util.spec_from_file_location("native_runtime", MODULE_PATH)
native = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(native)

SHA = "a" * 40


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def make_source(root: Path) -> tuple[Path, Path]:
    source = root / "source"
    for rel, content in {
        "Gemfile": 'source "https://rubygems.org"\n',
        "Gemfile.lock": "GEM\n\nPLATFORMS\n  x86_64-linux-gnu\n\nDEPENDENCIES\n\nBUNDLED WITH\n   2.6.7\n",
        "config/database.yml": "production:\n  adapter: sqlite3\n",
        "lib/redmine/version.rb": 'module Redmine; VERSION = "6.1.5"; end\n',
        "public/reqsys-e2e/evidence.json": '{"status":"passed"}\n',
        "config/initializers/secret_token.rb": 'RedmineApp::Application.config.secret_key_base = "ephemeral-test"\n',
        "files/sample.txt": "attachment\n",
        "app/models/example.rb": "class Example; end\n",
    }.items():
        path = source / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    artifacts = {}
    for rel in (
        "Gemfile.lock",
        "config/database.yml",
        "lib/redmine/version.rb",
        "public/reqsys-e2e/evidence.json",
    ):
        artifacts[rel] = hashlib.sha256((source / rel).read_bytes()).hexdigest()
    manifest = {
        "schema_version": 1,
        "source_identity": {
            "schema_version": 1,
            "repository": native.REPOSITORY,
            "source_sha": SHA,
            "source_runtime_sha256": "b" * 64,
            "provenance_method": "github_hosted_verified_copy",
            "scope": "tracked_build_source_not_deployment_authorization",
        },
        "redmine_version": "6.1.5.stable",
        "reqsys_sha": "c" * 40,
        "test_harness": {"source_sha": "d" * 40, "blob_sha": "e" * 40},
        "evidence_scope": "isolated_build_not_post_deploy_or_pc24x7",
        "artifacts_sha256": artifacts,
    }
    write_json(source / native.RELEASE_MANIFEST, manifest)

    db_path = root / "seed.sqlite3"
    db = sqlite3.connect(db_path)
    try:
        db.execute("create table markers(id integer primary key, value text not null)")
        db.execute("insert into markers(value) values ('persisted')")
        db.commit()
    finally:
        db.close()
    return source, db_path


class NativeRuntimeTests(unittest.TestCase):
    def test_manifest_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, _ = make_source(Path(tmp))
            native.verify_source_manifest(source, SHA)
            with (source / "Gemfile.lock").open("a", encoding="utf-8") as stream:
                stream.write("tamper\n")
            with self.assertRaisesRegex(native.NativeRuntimeError, "NATIVE_SOURCE_ARTIFACT_MISMATCH"):
                native.verify_source_manifest(source, SHA)

    def test_install_idempotent_and_state_is_outside_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, seed = make_source(root)
            target = root / "target"
            old = os.environ.get("REQSYS_NATIVE_TEST_MODE")
            os.environ["REQSYS_NATIVE_TEST_MODE"] = "1"
            try:
                first = native.install_release(source, target, SHA, seed_sqlite=seed, install_bundle=False)
                second = native.install_release(source, target, SHA, seed_sqlite=seed, install_bundle=False)
            finally:
                if old is None:
                    os.environ.pop("REQSYS_NATIVE_TEST_MODE", None)
                else:
                    os.environ["REQSYS_NATIVE_TEST_MODE"] = old
            self.assertEqual(first, second)
            current = target / "current"
            self.assertTrue(current.is_symlink())
            release = current.resolve()
            self.assertEqual(release.name, SHA)
            for rel in ("files", "tmp", "log", "config/initializers/secret_token.rb"):
                self.assertTrue((release / rel).is_symlink(), rel)
            self.assertEqual((target / "shared/files/sample.txt").read_text(), "attachment\n")
            db = sqlite3.connect(f"file:{target / 'shared/db/redmine.sqlite3'}?mode=ro", uri=True)
            try:
                self.assertEqual(db.execute("select value from markers").fetchone(), ("persisted",))
            finally:
                db.close()
            self.assertEqual(native.verify_install(target, SHA), first)

    def test_skip_bundle_is_test_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, seed = make_source(root)
            old = os.environ.pop("REQSYS_NATIVE_TEST_MODE", None)
            try:
                with self.assertRaisesRegex(native.NativeRuntimeError, "NATIVE_SKIP_BUNDLE_NOT_ALLOWED"):
                    native.install_release(source, root / "target", SHA, seed_sqlite=seed, install_bundle=False)
            finally:
                if old is not None:
                    os.environ["REQSYS_NATIVE_TEST_MODE"] = old

    def test_wrong_sha_fails_before_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, seed = make_source(root)
            target = root / "target"
            old = os.environ.get("REQSYS_NATIVE_TEST_MODE")
            os.environ["REQSYS_NATIVE_TEST_MODE"] = "1"
            try:
                with self.assertRaisesRegex(native.NativeRuntimeError, "NATIVE_SOURCE_IDENTITY_MISMATCH"):
                    native.install_release(source, target, "f" * 40, seed_sqlite=seed, install_bundle=False)
            finally:
                if old is None:
                    os.environ.pop("REQSYS_NATIVE_TEST_MODE", None)
                else:
                    os.environ["REQSYS_NATIVE_TEST_MODE"] = old
            self.assertFalse(target.exists())

    def test_backup_tamper_restore_and_independent_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, seed = make_source(root)
            target = root / "target"
            old = os.environ.get("REQSYS_NATIVE_TEST_MODE")
            os.environ["REQSYS_NATIVE_TEST_MODE"] = "1"
            try:
                native.install_release(source, target, SHA, seed_sqlite=seed, install_bundle=False)
            finally:
                if old is None:
                    os.environ.pop("REQSYS_NATIVE_TEST_MODE", None)
                else:
                    os.environ["REQSYS_NATIVE_TEST_MODE"] = old
            backup = root / "backup"
            native.backup_sqlite(target / "shared", backup, quiesced=True)
            original = (backup / "db/redmine.sqlite3").read_bytes()
            with (backup / "db/redmine.sqlite3").open("ab") as stream:
                stream.write(b"tamper")
            with self.assertRaisesRegex(native.NativeRuntimeError, "NATIVE_BACKUP_HASH_MISMATCH"):
                native.verify_backup(backup)
            (backup / "db/redmine.sqlite3").write_bytes(original)
            native.verify_backup(backup)
            restored = root / "restored"
            native.restore_sqlite(backup, restored)
            db = sqlite3.connect(f"file:{restored / 'db/redmine.sqlite3'}?mode=ro", uri=True)
            try:
                self.assertEqual(db.execute("pragma integrity_check").fetchone(), ("ok",))
                self.assertEqual(db.execute("select value from markers").fetchone(), ("persisted",))
            finally:
                db.close()
            self.assertEqual((restored / "files/sample.txt").read_text(), "attachment\n")
            self.assertTrue((restored / "config/secret_token.rb").is_file())

    def test_backup_requires_quiesce(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            (state / "db").mkdir(parents=True)
            sqlite3.connect(state / "db/redmine.sqlite3").close()
            with self.assertRaisesRegex(native.NativeRuntimeError, "NATIVE_BACKUP_REQUIRES_QUIESCE"):
                native.backup_sqlite(state, root / "backup", quiesced=False)

    def test_service_shutdown_preserves_readiness_failure(self):
        with self.assertRaisesRegex(native.NativeRuntimeError, "NATIVE_E2E_HTTP_NOT_READY"):
            native.validate_service_shutdown(False, False, 99)

    def test_service_shutdown_accepts_only_intentional_sigterm(self):
        for code in (0, -15, 143):
            native.validate_service_shutdown(True, True, code)
        with self.assertRaisesRegex(native.NativeRuntimeError, "NATIVE_E2E_SERVICE_EXITED_BEFORE_STOP"):
            native.validate_service_shutdown(True, False, 0)
        with self.assertRaisesRegex(native.NativeRuntimeError, "NATIVE_E2E_SERVICE_EXIT_INVALID"):
            native.validate_service_shutdown(True, True, 99)

    def test_systemd_contract_has_no_render_or_docker_dependency(self):
        unit = (Path(__file__).resolve().parents[1] / "systemd/reqsys-redmine.service").read_text(encoding="utf-8")
        lowered = unit.lower()
        self.assertNotIn("render", lowered)
        self.assertNotIn("docker", lowered)
        self.assertIn("ExecStart=/opt/reqsys-redmine/current/bin/reqsys-redmine-start", unit)
        self.assertIn("ProtectSystem=strict", unit)
        self.assertIn("ReadWritePaths=/opt/reqsys-redmine/shared", unit)
        self.assertIn("EnvironmentFile=/etc/reqsys-redmine/redmine.env", unit)


if __name__ == "__main__":
    unittest.main()
