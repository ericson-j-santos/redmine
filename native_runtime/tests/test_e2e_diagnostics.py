import sys
from pathlib import Path
import tempfile
import unittest

RUNTIME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNTIME))
import e2e_portability as e2e  # noqa: E402


class E2EDiagnosticTests(unittest.TestCase):
    def test_release_seal_preserves_external_state_and_is_reversible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = root / "release"
            nested = release / "public/assets"
            nested.mkdir(parents=True)
            manifest = nested / ".manifest.json"
            manifest.write_text('{"assets":{}}\n', encoding="utf-8")
            executable = release / "bin/start"
            executable.parent.mkdir(parents=True)
            executable.write_text("#!/bin/sh\n", encoding="utf-8")
            executable.chmod(0o755)
            shared = root / "shared/tmp"
            shared.mkdir(parents=True)
            shared_file = shared / "runtime.txt"
            shared_file.write_text("mutable\n", encoding="utf-8")
            (release / "tmp").symlink_to(shared, target_is_directory=True)

            original = {
                ".": release.stat().st_mode & 0o7777,
                "public/assets": nested.stat().st_mode & 0o7777,
                "public/assets/.manifest.json": manifest.stat().st_mode & 0o7777,
                "bin/start": executable.stat().st_mode & 0o7777,
            }
            shared_mode = shared_file.stat().st_mode & 0o7777
            modes = e2e.seal_release_for_runtime(release)
            try:
                for path in (release, nested, manifest, executable):
                    self.assertEqual(path.stat().st_mode & 0o222, 0, path)
                self.assertEqual(executable.stat().st_mode & 0o111, 0o111)
                self.assertEqual(shared_file.stat().st_mode & 0o7777, shared_mode)
                self.assertTrue((release / "tmp").is_symlink())
            finally:
                e2e.restore_release_modes(release, modes)

            for rel, expected_mode in original.items():
                path = release if rel == "." else release / rel
                self.assertEqual(path.stat().st_mode & 0o7777, expected_mode, rel)

    def test_log_tail_redacts_sensitive_values_and_limits_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "puma.log"
            secret = "sensitive-value-12345"
            lines = [f"line-{index}" for index in range(45)]
            lines.append(f"secret={secret}")
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            tail = e2e.sanitized_log_tail(
                path,
                {"SECRET_KEY_BASE": secret, "VISIBLE_SETTING": "visible"},
            )
            self.assertNotIn(secret, tail)
            self.assertIn("[REDACTED]", tail)
            self.assertNotIn("line-0", tail)
            self.assertIn("line-44", tail)


if __name__ == "__main__":
    unittest.main()
