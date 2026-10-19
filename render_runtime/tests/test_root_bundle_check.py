"""Contratos do candidato da raiz; Bundler e Rails reais são verificados no CI."""
import unittest
from unittest.mock import patch
from render_runtime import root_bundle_check as target


class RootBundlePolicyTests(unittest.TestCase):
    def test_upstream_change_and_partial_patch_rejected(self):
        for value in (b"", b"# edited", b"gem 'mail', '2.9.1'"):
            with self.assertRaisesRegex(ValueError, "SOURCE_CHANGED"):
                target.candidate_gemfile(value)

    def test_only_expected_declarations_are_changed(self):
        original = "\n".join(target.REPLACEMENTS) + "\n# keep-me\n"
        with patch.object(target, "SOURCE_GEMFILE_BLOB", target.blob_sha(original.encode())):
            result = target.candidate_gemfile(original.encode()).decode()
        self.assertEqual(result, "\n".join(target.REPLACEMENTS.values()) + "\n# keep-me\n")

    def test_duplicate_declaration_rejected(self):
        original = "\n".join(target.REPLACEMENTS) + "\n" + next(iter(target.REPLACEMENTS))
        with patch.object(target, "SOURCE_GEMFILE_BLOB", target.blob_sha(original.encode())):
            with self.assertRaisesRegex(ValueError, "AMBIGUOUS"):
                target.candidate_gemfile(original.encode())

    def test_positive_summary_and_replay(self):
        text = "52 runs, 166 assertions, 0 failures, 0 errors, 0 skips\n"
        self.assertEqual(target.require_suite(text), target.require_suite(text))
        self.assertEqual(target.require_suite(text)["runs"], 52)

    def test_invalid_and_skipped_suites_fail(self):
        for text in ("", "success", "0 runs, 0 assertions, 0 failures, 0 errors, 0 skips",
                     "52 runs, 166 assertions, 0 failures, 0 errors, 1 skips",
                     "52 runs, 166 assertions, 1 failures, 0 errors, 0 skips"):
            with self.assertRaises(ValueError):
                target.require_suite(text)

    def test_duplicate_summary_rejected(self):
        text = "52 runs, 166 assertions, 0 failures, 0 errors, 0 skips\n" * 2
        with self.assertRaises(ValueError):
            target.require_suite(text)


if __name__ == "__main__":
    unittest.main()
