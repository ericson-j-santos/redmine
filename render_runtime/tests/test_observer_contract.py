"""Políticas locais; instalação e boot reais são exigidos no executor Ruby."""
import unittest
from unittest.mock import patch
from render_runtime import root_bundle_check as target


class ObserverContractTests(unittest.TestCase):
    original = b"GEM\n  remote: https://rubygems.org/\n  specs:\n    mail (2.9.1)\n\nDEPENDENCIES\n  mail (= 2.9.1)\n\nRUBY VERSION\n   ruby 3.3.12p206\n"
    updated = original.replace(b"    mail (2.9.1)\n", b"    mail (2.9.1)\n    observer (0.1.2)\n").replace(b"  mail (= 2.9.1)\n", b"  mail (= 2.9.1)\n  observer (= 0.1.2)\n")
    gemfile = b"group :test do\n" + target.OBSERVER_LINE + b"end\n"

    def test_only_observer_addition_and_replay(self):
        for _ in range(2):
            target.require_observer_only_change(self.original, self.updated)
            target.require_observer_contract(self.gemfile, self.updated)

    def test_existing_graph_and_metadata_changes_rejected(self):
        for changed in (self.updated.replace(b"2.9.1", b"2.9.2"),
                        self.updated.replace(b"rubygems.org", b"other.invalid"),
                        self.updated.replace(b"3.3.12p206", b"3.4.11p1"),
                        self.updated + b"PLATFORMS\n  changed\n"):
            with self.assertRaisesRegex(ValueError, "CHANGED_EXISTING_LOCK"):
                target.require_observer_only_change(self.original, changed)

    def test_missing_duplicate_or_wrong_observer_rejected(self):
        for changed in (self.original, self.updated + b"    observer (0.1.2)\n",
                        self.updated.replace(b"0.1.2", b"0.1.3"),
                        self.updated.replace(b"  observer (= 0.1.2)\n", b"")):
            with self.assertRaises(ValueError):
                target.require_observer_only_change(self.original, changed)

    def test_test_group_and_lock_required(self):
        for changed in (b"", self.gemfile.replace(b":test", b":production"),
                        self.gemfile + target.OBSERVER_LINE):
            with self.assertRaisesRegex(ValueError, "TEST_DEPENDENCY_MISSING"):
                target.require_observer_contract(changed, self.updated)
        with self.assertRaisesRegex(ValueError, "LOCK_INVALID"):
            target.require_observer_contract(self.gemfile, self.original)

    def test_candidate_preserves_other_bytes(self):
        raw = b"# keep\ngroup :test do\n  gem 'factory_bot_rails'\nend\n"
        with patch.object(target, "OBSERVER_GEMFILE_BLOB", target.blob_sha(raw)):
            actual = target.observer_candidate_gemfile(raw)
        self.assertEqual(actual.replace(target.OBSERVER_LINE, b""), raw)
        self.assertEqual(actual.count(target.OBSERVER_LINE), 1)

    def test_changed_source_and_repeat_candidate_fail_closed(self):
        for raw in (b"", self.gemfile, b"group :test do\nend\n"):
            with self.assertRaisesRegex(ValueError, "SOURCE_CHANGED"):
                target.observer_candidate_gemfile(raw)

    def test_ambiguous_test_group_rejected(self):
        raw = b"group :test do\nend\n" * 2
        with patch.object(target, "OBSERVER_GEMFILE_BLOB", target.blob_sha(raw)):
            with self.assertRaisesRegex(ValueError, "AMBIGUOUS"):
                target.observer_candidate_gemfile(raw)
