"""Regressão da falha Redmine::Utils observada no build integral."""
from pathlib import Path
import unittest

BUILD = Path(__file__).resolve().parents[1] / "build_redmine_6_1_4.sh"


class VersionObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = BUILD.read_text(encoding="utf-8")

    def test_observation_uses_initialized_rails(self):
        self.assertIn(
            "RAILS_ENV=production bundle exec rails runner 'print Redmine::VERSION.to_s'",
            self.text,
        )
        self.assertNotIn("bundle exec ruby -Ilib -rredmine/version", self.text)

    def test_observation_follows_fresh_database_setup(self):
        setup = self.text.index("RAILS_ENV=production bundle exec rails db:migrate")
        probe = self.text.index('STAGE="version_observation"')
        bootstrap = self.text.index('rails runner "${ROOT}/render_runtime/bootstrap.rb"')
        self.assertLess(setup, probe)
        self.assertLess(probe, bootstrap)

    def test_mismatch_blocks_before_listening_or_publishing(self):
        gate = self.text.index('echo "REDMINE_OBSERVED_VERSION_MISMATCH" >&2; exit 2')
        self.assertLess(gate, self.text.index('STAGE="puma_readiness"'))
        self.assertLess(gate, self.text.index('STAGE="evidence_validation"'))
        self.assertIn('export REDMINE_VERSION="${OBSERVED_REDMINE_VERSION}"', self.text)

    def test_source_integrity_and_disposable_scope_remain_first(self):
        reserve = self.text.index('runtime_safety.py" reserve')
        checksum = self.text.index("sha256sum --check -")
        setup = self.text.index("bundle exec rails db:migrate")
        self.assertLess(reserve, checksum)
        self.assertLess(checksum, setup)
        self.assertNotIn("rm -rf", self.text)


if __name__ == "__main__":
    unittest.main()
