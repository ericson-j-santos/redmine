"""Contratos locais; a prova Rails real é executada pelo root_bundle_check."""
from pathlib import Path
import runpy
import unittest

target = runpy.run_path(str(Path(__file__).resolve().parents[1] / "root_bundle_check.py"))


class SpentHoursContractTests(unittest.TestCase):
    def test_isolated_branch_is_verify_only(self):
        self.assertTrue(target["allowed_ref"](target["SPENT_HOURS_REF"], "verify"))
        for mode in ("candidate", "ruby-metadata", "observer-candidate"):
            self.assertFalse(target["allowed_ref"](target["SPENT_HOURS_REF"], mode))

    def test_other_branches_are_rejected(self):
        for ref in (None, "", "refs/heads/main", "refs/pull/1/merge",
                    target["SPENT_HOURS_REF"] + "-other"):
            self.assertFalse(target["allowed_ref"](ref, "verify"))
        self.assertTrue(target["allowed_ref"](target["DEV_REF"], "verify"))

    def test_fixture_mutation_preserves_all_other_bytes(self):
        fixed = b"fixtures :member_roles, :enumerations\n# preserved\n"
        self.assertEqual(b"fixtures :member_roles, :activities\n# preserved\n",
                         target["fixture_negative_source"](fixed))

    def test_ambiguous_changed_and_repeat_fixture_mutations_are_rejected(self):
        fixed = b"fixtures :member_roles, :enumerations\n"
        for raw in (b"", fixed * 2, target["fixture_negative_source"](fixed)):
            with self.assertRaisesRegex(ValueError, "FIXTURE_CONTRACT_INVALID"):
                target["fixture_negative_source"](raw)

    def test_real_fixture_rejection_requires_specific_error_and_summary(self):
        text = "ArgumentError: No fixture files found for activities\n"
        text += "1 runs, 0 assertions, 0 failures, 1 errors, 0 skips\n"
        target["require_fixture_rejection"](1, text)
        target["require_fixture_rejection"](1, text)
        for code, bad in ((0, text), (124, text), (1, text + text),
                          (1, text.replace("activities", "another_fixture")),
                          (1, text.replace("1 errors", "2 errors")),
                          (1, text.replace("0 skips", "1 skips"))):
            with self.assertRaisesRegex(ValueError, "NEGATIVE_CONTROL_FAILED"):
                target["require_fixture_rejection"](code, bad)

    def test_complete_suites_and_replay(self):
        for name, (_, minimum) in target["SPENT_HOURS_SUITES"].items():
            text = f"{minimum} runs, 50 assertions, 0 failures, 0 errors, 0 skips"
            observed = target["require_spent_hours_suite"](name, text)
            self.assertEqual(minimum, observed["runs"])
            self.assertEqual(observed, target["require_spent_hours_suite"](name, text))

    def test_reduced_coverage_is_not_success(self):
        for name, (_, minimum) in target["SPENT_HOURS_SUITES"].items():
            with self.assertRaisesRegex(ValueError, "COVERAGE_REDUCED"):
                target["require_spent_hours_suite"](
                    name, f"{minimum - 1} runs, 50 assertions, 0 failures, 0 errors, 0 skips")

    def test_failed_skipped_empty_or_duplicate_suite_is_rejected(self):
        good = "19 runs, 50 assertions, 0 failures, 0 errors, 0 skips"
        for text in ("", good + "\n" + good,
                     good.replace("0 failures", "1 failures"),
                     good.replace("0 errors", "1 errors"),
                     good.replace("0 skips", "1 skips")):
            with self.assertRaises(ValueError):
                target["require_spent_hours_suite"]("spent_hours_integration", text)

    def test_unknown_suite_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "SUITE_UNKNOWN"):
            target["require_spent_hours_suite"]("foreign", "19 runs, 50 assertions, 0 failures, 0 errors, 0 skips")


if __name__ == "__main__":
    unittest.main()
