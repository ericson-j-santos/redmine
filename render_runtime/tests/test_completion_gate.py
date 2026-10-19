"""Controle de falso positivo; os testes Ruby reais executam no job integral."""
import unittest

from render_runtime.completion_gate import CompletionGateError, require_complete_suites


class CompleteSuitesTests(unittest.TestCase):
    def setUp(self):
        self.good = {
            "attachment": "46 runs, 142 assertions, 0 failures, 0 errors, 0 skips\n",
            "mailer": "83 runs, 459 assertions, 0 failures, 0 errors, 0 skips\n",
        }

    def test_accepts_both_complete_suites_and_replay(self):
        first = require_complete_suites(self.good)
        self.assertEqual(first["attachment"]["runs"], 46)
        for _ in range(3):
            self.assertEqual(require_complete_suites(self.good), first)

    def test_previous_one_skipped_summary_fails(self):
        self.good["attachment"] = "46 runs, 140 assertions, 0 failures, 0 errors, 1 skips"
        with self.assertRaisesRegex(CompletionGateError, "NOT_PASSED"):
            require_complete_suites(self.good)

    def test_missing_or_extra_suite_fails(self):
        for value in ({}, {"mailer": self.good["mailer"]}, dict(self.good, other="")):
            with self.subTest(suites=list(value)):
                with self.assertRaises(CompletionGateError):
                    require_complete_suites(value)

    def test_empty_duplicate_skipped_failed_or_error_summary_fails(self):
        for text in ("", "success", self.good["mailer"] * 2,
                     "0 runs, 0 assertions, 0 failures, 0 errors, 0 skips",
                     "10 runs, 10 assertions, 1 failures, 0 errors, 0 skips",
                     "10 runs, 10 assertions, 0 failures, 1 errors, 0 skips",
                     "10 runs, 10 assertions, 0 failures, 0 errors, 10 skips"):
            with self.subTest(summary=text):
                with self.assertRaises(CompletionGateError):
                    require_complete_suites(dict(self.good, mailer=text))

    def test_invalid_log_type_and_size_fail(self):
        for text in (None, [], "x" * 2_000_001):
            with self.subTest(kind=type(text).__name__):
                with self.assertRaises(CompletionGateError):
                    require_complete_suites(dict(self.good, attachment=text))


if __name__ == "__main__":
    unittest.main()
