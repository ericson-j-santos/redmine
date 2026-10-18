"""Regressão do recurso HTTP aberto em respostas de erro/redirect."""
import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from render_runtime import runtime_safety as safety


class HTTPErrorCleanupTests(unittest.TestCase):
    def test_http_error_body_is_closed_without_exposing_content(self):
        body = io.BytesIO(b"private response body")
        error = HTTPError("http://127.0.0.1:3000", 403, "denied", {}, body)
        env = {
            "REDMINE_BASE_URL": "http://127.0.0.1:3000",
            "REQSYS_REDMINE_API_KEY": "a" * 40,
        }
        with patch.object(safety, "build_opener") as factory:
            factory.return_value.open.side_effect = error
            with self.assertRaisesRegex(safety.SafetyError, "^REDMINE_PROJECT_LOOKUP_FAILED$"):
                safety.resolve_project(env)
        self.assertTrue(body.closed)


if __name__ == "__main__":
    unittest.main()
