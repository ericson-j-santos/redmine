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

    def test_real_frozen_rejection_is_required(self):
        target.require_frozen_rejection(16, "Cannot update lockfile in frozen mode")
        for code, output in ((0, "frozen"), (1, "network failure"), (16, "unrelated error")):
            with self.assertRaisesRegex(ValueError, "FROZEN_CONTROL_FAILED"):
                target.require_frozen_rejection(code, output)


    def test_root_ruby_floor_matches_security_dependency_and_historical_jobs(self):
        from pathlib import Path
        import re

        root = Path(__file__).resolve().parents[2]
        gemfile = (root / "Gemfile").read_text(encoding="utf-8")
        workflow = (root / ".github/workflows/linters.yml").read_text(encoding="utf-8")
        self.assertIn("ruby '>= 3.3.0', '< 3.5.0'", gemfile)
        for job in ("lint", "bundle-audit"):
            match = re.search(rf"(?ms)^  {job}:\n(.*?)(?=^  [\w-]+:|\Z)", workflow)
            self.assertIsNotNone(match)
            versions = re.findall(r"ruby-version: ['\\\"]?([0-9]+\.[0-9]+)", match.group(1))
            self.assertEqual(versions, ["3.3"])
        self.assertIn("bundle exec rubocop --parallel", workflow)
        self.assertIn("bundle exec bundle audit check --update", workflow)

    def test_metadata_only_change_preserves_graph(self):
        original = b"GEM\n  specs:\n    example (1.0)\n\nRUBY VERSION\n   ruby 3.2.3p157\n\nBUNDLED WITH\n   2.6.7\n"
        updated = original.replace(b"3.2.3p157", b"3.3.12p9")
        self.assertEqual(target.require_metadata_only_change(original, updated), "3.3.12p9")
        with self.assertRaisesRegex(ValueError, "CHANGED_DEPENDENCIES"):
            target.require_metadata_only_change(original, updated.replace(b"example (1.0)", b"example (2.0)"))

    def test_bad_ruby_metadata_is_rejected(self):
        original = b"GEM\n\nRUBY VERSION\n   ruby 3.2.3p157\n\nBUNDLED WITH\n   2.6.7\n"
        for updated in (original, b"", original + original,
                        original.replace(b"3.2.3p157", b"3.5.0p1"),
                        original.replace(b"3.2.3p157", b"3.3.0-rc1")):
            with self.assertRaises(ValueError):
                target.require_metadata_only_change(original, updated)

    def test_committed_ruby_metadata_is_supported(self):
        from pathlib import Path

        lock = (Path(__file__).resolve().parents[2] / "Gemfile.lock").read_bytes()
        version = target.require_metadata_only_change(lock, lock)
        self.assertIn(version.split(".")[:2], (["3", "3"], ["3", "4"]))

if __name__ == "__main__":
    unittest.main()
