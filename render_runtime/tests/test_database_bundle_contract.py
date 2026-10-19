"""Regressões de bytes preservados; o DSL, Bundler e bancos são exercitados no CI."""
import unittest
from unittest.mock import patch
from render_runtime import database_bundle_contract as target

BEFORE = (
    b"GEM\n"
    b"  remote: https://rubygems.org/\n"
    b"  specs:\n"
    b"    activemodel (8.0.5.1)\n"
    b"    activerecord (8.0.5.1)\n"
    b"      activemodel (= 8.0.5.1)\n"
    b"    bigdecimal (4.1.3)\n"
    b"\n"
    b"PLATFORMS\n"
    b"  x86_64-linux-gnu\n"
    b"\n"
    b"DEPENDENCIES\n"
    b"  activerecord (= 8.0.5.1)\n"
    b"  bigdecimal\n"
    b"\n"
    b"RUBY VERSION\n"
    b"   ruby 3.3.12p206\n"
    b"\n"
    b"BUNDLED WITH\n"
    b"   2.6.7\n"
)
MYSQL_SPEC = b"    mysql2 (0.5.7)\n      bigdecimal\n"
ADVISORY_SPEC = b"    with_advisory_lock (7.6.0)\n      activerecord (>= 7.2)\n"
AFTER = BEFORE.replace(
    b"\n\nPLATFORMS\n", b"\n" + MYSQL_SPEC + ADVISORY_SPEC + b"\nPLATFORMS\n",
).replace(
    b"\n\nRUBY VERSION\n",
    b"\n  mysql2 (~> 0.5.0)\n  with_advisory_lock\n\nRUBY VERSION\n",
)


class DatabaseBundleContractTests(unittest.TestCase):
    def test_additive_change_and_replay(self):
        for _ in range(2):
            target.require_database_only_additions(BEFORE, AFTER)
            target.require_database_contract(AFTER)

    def test_existing_bytes_must_remain_identical(self):
        changes = (
            (b"    bigdecimal (4.1.3)\n", b"    bigdecimal (4.1.4)\n"),
            (b"    bigdecimal (4.1.3)\n", b""),
            (b"      activemodel (= 8.0.5.1)\n", b"      activemodel (>= 8.0.5.1)\n"),
            (b"  activerecord (= 8.0.5.1)\n", b"  activerecord (>= 8.0.5.1)\n"),
            (b"https://rubygems.org/", b"https://example.invalid/"),
            (b"  x86_64-linux-gnu\n", b"  x86_64-linux-gnu\n  aarch64-linux-gnu\n"),
            (b"ruby 3.3.12p206", b"ruby 3.3.13p206"),
            (b"   2.6.7\n", b"   2.6.8\n"),
        )
        for old, new in changes:
            with self.subTest(old=old):
                self.assertIn(old, AFTER)
                with self.assertRaises(ValueError):
                    target.require_database_only_additions(BEFORE, AFTER.replace(old, new, 1))

    def test_unreviewed_additions_and_duplicate_entries_fail(self):
        candidates = (
            AFTER.replace(b"mysql2 (0.5.7)", b"mysql2 (0.5.8)", 1),
            AFTER.replace(MYSQL_SPEC, MYSQL_SPEC + b"      unreviewed_dependency\n", 1),
            AFTER.replace(b"\n\nPLATFORMS\n", b"\n    unreviewed (1.0)\n\nPLATFORMS\n", 1),
            AFTER.replace(MYSQL_SPEC, MYSQL_SPEC * 2, 1),
            AFTER.replace(ADVISORY_SPEC, b"", 1),
            AFTER.replace(b"  mysql2 (~> 0.5.0)\n", b"  mysql2 (>= 0.5.0)\n", 1),
            AFTER.replace(b"  mysql2 (~> 0.5.0)\n", b"  mysql2 (~> 0.5.0)\n" * 2, 1),
            AFTER.replace(b"\nRUBY VERSION\n", b"\nCHECKSUMS\n  unreviewed\n\nRUBY VERSION\n", 1),
        )
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                with self.assertRaises(ValueError):
                    target.require_database_only_additions(BEFORE, candidate)

    def test_block_cannot_hide_in_another_section(self):
        candidate = AFTER.replace(MYSQL_SPEC, b"", 1).replace(
            b"DEPENDENCIES\n", b"DEPENDENCIES\n" + MYSQL_SPEC, 1
        )
        with self.assertRaises(ValueError):
            target.require_database_only_additions(BEFORE, candidate)

    def test_block_cannot_split_existing_dependencies(self):
        candidate = AFTER.replace(MYSQL_SPEC, b"", 1).replace(
            b"    activerecord (8.0.5.1)\n", b"    activerecord (8.0.5.1)\n" + MYSQL_SPEC, 1
        )
        with self.assertRaises(ValueError):
            target.require_database_only_additions(BEFORE, candidate)

    def test_missing_additions_or_reapplication_fail(self):
        for original, updated in (
            (BEFORE, BEFORE), (AFTER, AFTER),
            (BEFORE, AFTER.replace(b"  with_advisory_lock\n", b"", 1)),
        ):
            with self.assertRaises(ValueError):
                target.require_database_only_additions(original, updated)

    def test_invalid_format_fails_closed(self):
        for invalid in (
            b"", b"not a lock\n", AFTER.replace(b"\n", b"\r\n"), AFTER + b"\0", AFTER + AFTER,
        ):
            with self.assertRaises(ValueError):
                target.require_database_only_additions(BEFORE, invalid)

    def test_candidate_preserves_source_and_rejects_reapplication(self):
        import hashlib

        raw = b"# keep\n" + target.OBSERVER_MARKER + b"  gem 'factory_bot_rails'\nend\n"
        digest = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        with patch.object(target, "SOURCE_GEMFILE_BLOB", digest):
            result = target.candidate_gemfile(raw)
            self.assertEqual(result.replace(target.DATABASE_TEST_ADDITIONS, b"", 1), raw)
            with self.assertRaisesRegex(ValueError, "SOURCE_CHANGED"):
                target.candidate_gemfile(result)
        for changed in (b"", raw, b"group :test do\nend\n"):
            with self.assertRaisesRegex(ValueError, "SOURCE_CHANGED"):
                target.candidate_gemfile(changed)


if __name__ == "__main__":
    unittest.main()
