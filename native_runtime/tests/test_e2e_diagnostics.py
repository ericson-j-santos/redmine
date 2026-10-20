import sys
from pathlib import Path
import tempfile
import unittest

RUNTIME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNTIME))
import e2e_portability as e2e  # noqa: E402


class E2EDiagnosticTests(unittest.TestCase):
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
