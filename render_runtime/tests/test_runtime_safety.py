"""Controles locais: SQLite real, concorrência e HTTP loopback; não é E2E Redmine."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from render_runtime import runtime_safety as safety

ENV = {
    "REQSYS_REDMINE_EPHEMERAL_E2E": "1",
    "REQSYS_REDMINE_API_KEY": "a" * 40,
    "REQSYS_REDMINE_PROJECT_IDENTIFIER": "reqsys-e2e-dev",
}


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def test_fresh_reservation_is_private(self):
        runtime = safety.reserve_runtime(self.root, ENV)
        self.assertEqual(runtime, self.root / ".runtime")
        self.assertTrue(runtime.is_dir())
        if os.name != "nt":
            self.assertEqual(runtime.stat().st_mode & 0o777, 0o700)

    def test_existing_sqlite_is_preserved_on_replay(self):
        runtime = self.root / ".runtime"
        runtime.mkdir()
        db_path = runtime / "important.sqlite3"
        with sqlite3.connect(db_path) as db:
            db.execute("CREATE TABLE sentinel (value TEXT)")
            db.execute("INSERT INTO sentinel VALUES ('preserve-me')")
        before = hashlib.sha256(db_path.read_bytes()).hexdigest()
        for _ in range(3):
            with self.assertRaisesRegex(safety.SafetyError, "EXISTS_PRESERVED"):
                safety.reserve_runtime(self.root, ENV)
        self.assertEqual(hashlib.sha256(db_path.read_bytes()).hexdigest(), before)
        with sqlite3.connect(db_path) as db:
            self.assertEqual(db.execute("SELECT value FROM sentinel").fetchall(),
                             [("preserve-me",)])

    def test_concurrent_reservation_has_one_winner(self):
        barrier = threading.Barrier(8)
        def reserve(_):
            barrier.wait(timeout=5)
            try:
                safety.reserve_runtime(self.root, ENV)
                return "won"
            except safety.SafetyError as exc:
                return str(exc)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(reserve, range(8)))
        self.assertEqual(results.count("won"), 1)
        self.assertEqual(results.count("REDMINE_RUNTIME_EXISTS_PRESERVED"), 7)

    def test_missing_scope_has_no_filesystem_effect(self):
        with self.assertRaisesRegex(safety.SafetyError, "SCOPE_NOT_CONFIRMED"):
            safety.reserve_runtime(self.root, {})
        self.assertEqual(list(self.root.iterdir()), [])

    def test_missing_key_has_no_filesystem_effect(self):
        env = dict(ENV)
        del env["REQSYS_REDMINE_API_KEY"]
        with self.assertRaisesRegex(safety.SafetyError, "KEY_REFERENCE_INVALID"):
            safety.reserve_runtime(self.root, env)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_invalid_identifier_has_no_filesystem_effect(self):
        for identifier in ("../prod", "", "A", "a?key=x", "a" * 101):
            with self.subTest(identifier=identifier):
                with self.assertRaisesRegex(safety.SafetyError, "IDENTIFIER_INVALID"):
                    safety.reserve_runtime(
                        self.root, dict(ENV, REQSYS_REDMINE_PROJECT_IDENTIFIER=identifier))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_existing_regular_file_is_preserved(self):
        existing = self.root / ".runtime"
        existing.write_bytes(b"must-survive")
        with self.assertRaisesRegex(safety.SafetyError, "EXISTS_PRESERVED"):
            safety.reserve_runtime(self.root, ENV)
        self.assertEqual(existing.read_bytes(), b"must-survive")

    def test_symlink_and_dangling_symlink_are_preserved(self):
        runtime = self.root / ".runtime"
        for target in (self.root, self.root / "does-not-exist"):
            with self.subTest(target=str(target)):
                runtime.symlink_to(target, target_is_directory=True)
                with self.assertRaisesRegex(safety.SafetyError, "EXISTS_PRESERVED"):
                    safety.reserve_runtime(self.root, ENV)
                self.assertTrue(runtime.is_symlink())
                runtime.unlink()  # Remove only the link created by this test.

    def test_relative_root_is_rejected(self):
        with self.assertRaisesRegex(safety.SafetyError, "ROOT_INVALID"):
            safety.reserve_runtime(Path("relative"), ENV)

    def test_cli_reservation_and_nonmutating_replay(self):
        fake_script = self.root / "render_runtime" / "runtime_safety.py"
        with patch.object(safety, "__file__", str(fake_script)), patch.dict(
            os.environ, ENV, clear=True
        ), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ) as err:
            self.assertEqual(safety.main(["reserve"]), 0)
            self.assertEqual(safety.main(["reserve"]), 2)
            self.assertIn("EXISTS_PRESERVED", err.getvalue())
            self.assertNotIn(ENV["REQSYS_REDMINE_API_KEY"], err.getvalue())


class ProjectTests(unittest.TestCase):
    def test_actual_non_one_id_is_used(self):
        payload = {"project": {"id": 42, "identifier": "reqsys-e2e-dev", "is_public": False}}
        for _ in range(3):
            self.assertEqual(safety.project_id(payload, "reqsys-e2e-dev"), 42)

    def test_id_types_are_strict(self):
        for value in (True, False, 0, -1, "1", 1.0, None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(safety.SafetyError, "ID_INVALID"):
                    safety.project_id({"project": {
                        "id": value, "identifier": "reqsys-e2e-dev", "is_public": False
                    }}, "reqsys-e2e-dev")

    def test_wrong_identity_is_rejected(self):
        with self.assertRaisesRegex(safety.SafetyError, "IDENTITY_MISMATCH"):
            safety.project_id({"project": {
                "id": 42, "identifier": "production", "is_public": False
            }}, "reqsys-e2e-dev")

    def test_public_or_unknown_visibility_is_rejected(self):
        for value in (True, None, 0, "false"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(safety.SafetyError, "NOT_PRIVATE"):
                    safety.project_id({"project": {
                        "id": 42, "identifier": "reqsys-e2e-dev", "is_public": value
                    }}, "reqsys-e2e-dev")

    def test_invalid_payload_shape_is_rejected(self):
        for value in (None, [], {}, {"project": []}):
            with self.subTest(value=value):
                with self.assertRaises(safety.SafetyError):
                    safety.project_id(value, "reqsys-e2e-dev")


class LoopbackHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requests = []
        cls.status = 200
        cls.body = b"{}"
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                cls.requests.append((self.path, self.headers.get("X-Redmine-API-Key")))
                self.send_response(cls.status)
                if cls.status == 302:
                    self.send_header("Location", "/must-not-follow")
                self.end_headers()
                self.wfile.write(cls.body)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(
            target=lambda: cls.server.serve_forever(poll_interval=0.01), daemon=True)
        cls.thread.start()
        cls.env = dict(ENV, REDMINE_BASE_URL=f"http://127.0.0.1:{cls.server.server_port}")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        type(self).requests = []
        type(self).status = 200
        type(self).body = json.dumps({"project": {
            "id": 42, "identifier": "reqsys-e2e-dev", "is_public": False
        }}).encode()

    def test_real_http_read_and_cli_return_observed_id(self):
        self.assertEqual(safety.resolve_project(self.env), 42)
        with patch.dict(os.environ, self.env, clear=True), contextlib.redirect_stdout(
            io.StringIO()
        ) as out:
            self.assertEqual(safety.main(["project"]), 0)
        self.assertEqual(out.getvalue(), "42\n")
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.requests[0], (
            "/projects/reqsys-e2e-dev.json", ENV["REQSYS_REDMINE_API_KEY"]))

    def test_redirect_does_not_forward_credential(self):
        type(self).status = 302
        with self.assertRaisesRegex(safety.SafetyError, "LOOKUP_FAILED"):
            safety.resolve_project(self.env)
        self.assertEqual(len(self.requests), 1)
        self.assertNotEqual(self.requests[0][0], "/must-not-follow")

    def test_http_error_never_exposes_body_or_key(self):
        type(self).status = 403
        type(self).body = ENV["REQSYS_REDMINE_API_KEY"].encode()
        with self.assertRaises(safety.SafetyError) as result:
            safety.resolve_project(self.env)
        self.assertEqual(str(result.exception), "REDMINE_PROJECT_LOOKUP_FAILED")

    def test_malformed_response_is_blocked(self):
        type(self).body = b"not-json"
        with self.assertRaisesRegex(safety.SafetyError, "RESPONSE_INVALID"):
            safety.resolve_project(self.env)

    def test_oversized_response_is_blocked(self):
        type(self).body = b"x" * (safety.MAX_RESPONSE_BYTES + 1)
        with self.assertRaisesRegex(safety.SafetyError, "RESPONSE_TOO_LARGE"):
            safety.resolve_project(self.env)

    def test_remote_or_ambiguous_urls_never_send_request(self):
        for value in (
            "https://example.com", "http://localhost:3000", "http://127.0.0.1",
            "http://127.0.0.1:0", "http://127.0.0.1:70000",
            "http://user@127.0.0.1:3000", "http://127.0.0.1:3000/path",
            "http://127.0.0.1:3000?token=x", "http://127.0.0.1:3000#x",
        ):
            with self.subTest(url=value):
                with self.assertRaisesRegex(safety.SafetyError, "LOOPBACK_URL_INVALID"):
                    safety.resolve_project(dict(self.env, REDMINE_BASE_URL=value))
        self.assertEqual(self.requests, [])



class BuildContractTests(unittest.TestCase):
    def setUp(self):
        self.source = (Path(__file__).resolve().parents[1]
                       / "build_redmine_6_1_4.sh").read_text(encoding="utf-8")

    def test_destructive_cleanup_is_absent(self):
        self.assertNotIn("rm -rf", self.source)
        self.assertNotIn("shutil.rmtree", self.source)

    def test_guard_precedes_download_or_bootstrap(self):
        guard = self.source.index('runtime_safety.py" reserve')
        self.assertLess(guard, self.source.index("curl --fail"))
        self.assertLess(guard, self.source.index("db:migrate"))

    def test_release_and_legacy_start_are_consistent(self):
        self.assertIn('REDMINE_VERSION="6.1.5"', self.source)
        self.assertIn('EXPECTED_SHA256="4b653d8863c012fdb226aedf6f8a18bdfa08d04625d15e8aafbbc3c4f6b70144"',
                      self.source)
        self.assertIn('LEGACY_START_DIR="${RUNTIME_ROOT}/redmine-6.1.4"', self.source)
        self.assertIn('ln -sT "redmine-6.1.5" "${LEGACY_START_DIR}"', self.source)
        self.assertIn('REDMINE_VERSION="${OBSERVED_REDMINE_VERSION}"', self.source)

    def test_harness_and_product_are_independently_pinned(self):
        self.assertIn('REQSYS_SHA="19905ca8580ebc567e5f7cd3d4b9b31a9aa21012"', self.source)
        self.assertIn('HARNESS_SOURCE_SHA="b84576f76fad584bc420cb447d046aaafdc775ba"', self.source)
        self.assertIn('HARNESS_BLOB_SHA="4008741f26abc4a1487978682ad53d17b9f20adc"', self.source)
        self.assertIn('hash-object "${HARNESS_PATH}"', self.source)
        self.assertIn('checkout -q --detach "${REQSYS_SHA}"', self.source)
        self.assertIn("unset PYTHONOPTIMIZE", self.source)

    def test_actual_project_and_isolated_database_are_required(self):
        self.assertIn('runtime_safety.py" project)', self.source)
        self.assertNotIn('export REDMINE_PROJECT_ID="1"', self.source)
        self.assertIn('DATABASE_URL="sqlite:///${RUNTIME_ROOT}/reqsys-e2e.sqlite3"', self.source)
        self.assertNotIn("sqlite:////tmp/", self.source)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "input.json"
        self.target = self.root / "published" / "evidence.json"
        text = (Path(__file__).resolve().parents[1]
                / "build_redmine_6_1_4.sh").read_text(encoding="utf-8")
        self.code = text.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
        self.env = dict(
            ENV, REQSYS_E2E_SHA="19905ca8580ebc567e5f7cd3d4b9b31a9aa21012",
            REQSYS_E2E_HARNESS_SHA="b84576f76fad584bc420cb447d046aaafdc775ba",
            REQSYS_E2E_HARNESS_BLOB="4008741f26abc4a1487978682ad53d17b9f20adc",
            REDMINE_VERSION="6.1.5.stable", REDMINE_PROJECT_ID="42")
        self.payload = {
            "status": "passed", "secret_values_in_evidence": False,
            "reqsys_sha": self.env["REQSYS_E2E_SHA"],
            "redmine": {"version": "6.1.5.stable", "project_id": 42},
            "correlation_id": "local-fixture-not-a-real-redmine-run",
            "positive": {"get_journals": True, "put_and_independent_readback": True,
                         "remote_state_imported": True, "journal_imported": True,
                         "replay_mutation_count": 0, "replay_audit_delta": 0},
            "negative": {"quarantined": True, "control_rows": 1}
        }

    def execute(self):
        self.source.write_text(json.dumps(self.payload), encoding="utf-8")
        with patch.dict(os.environ, self.env, clear=True), patch(
            "sys.argv", ["evidence", str(self.source), str(self.target)]
        ):
            exec(compile(self.code, "evidence_heredoc.py", "exec"), {})

    def test_positive_readback_records_both_source_versions(self):
        self.execute()
        readback = json.loads(self.target.read_text(encoding="utf-8"))
        self.assertEqual(readback["test_harness"]["blob_sha"],
                         self.env["REQSYS_E2E_HARNESS_BLOB"])
        self.assertEqual(readback["redmine"]["project_id"], 42)
        self.assertEqual(readback["evidence_scope"],
                         "isolated_build_not_post_deploy_or_pc24x7")

    def test_failed_evidence_is_not_published(self):
        self.payload["status"] = "failed"
        with self.assertRaisesRegex(SystemExit, "NOT_PASSED"):
            self.execute()
        self.assertFalse(self.target.exists())

    def test_actual_secret_is_detected_even_when_flag_claims_safe(self):
        self.payload["unexpected"] = ENV["REQSYS_REDMINE_API_KEY"]
        with self.assertRaisesRegex(SystemExit, "SECRET_DETECTED"):
            self.execute()
        self.assertFalse(self.target.exists())

    def test_other_product_sha_is_not_published(self):
        self.payload["reqsys_sha"] = "b" * 40
        with self.assertRaisesRegex(SystemExit, "REQSYS_SHA_MISMATCH"):
            self.execute()
        self.assertFalse(self.target.exists())

    def test_other_version_is_not_published(self):
        self.payload["redmine"]["version"] = "6.1.4.stable"
        with self.assertRaisesRegex(SystemExit, "VERSION_MISMATCH"):
            self.execute()
        self.assertFalse(self.target.exists())

    def test_other_project_is_not_published(self):
        self.payload["redmine"]["project_id"] = 1
        with self.assertRaisesRegex(SystemExit, "PROJECT_MISMATCH"):
            self.execute()
        self.assertFalse(self.target.exists())

    def test_passed_status_without_positive_proof_is_rejected(self):
        del self.payload["positive"]
        with self.assertRaisesRegex(SystemExit, "POSITIVE_PROOF_MISSING"):
            self.execute()
        self.assertFalse(self.target.exists())

    def test_existing_evidence_is_never_overwritten(self):
        self.execute()
        before = self.target.read_bytes()
        with self.assertRaises(FileExistsError):
            self.execute()
        self.assertEqual(self.target.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()