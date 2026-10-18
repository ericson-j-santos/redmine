"""Regressões do executor real isolado; não simulam sucesso do Redmine."""
from pathlib import Path
import unittest

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/linters.yml"


def full_build_section(text: str) -> str:
    marker = "\n  runtime-full-build:\n"
    if text.count(marker) != 1:
        raise ValueError("FULL_BUILD_JOB_MISSING_OR_DUPLICATED")
    return text.split(marker, 1)[1]


class FullBuildWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_real_entrypoint_and_bounded_process_are_required(self):
        section = full_build_section(self.text)
        self.assertIn('["bash", "render_runtime/build_redmine_6_1_4.sh"]', section)
        self.assertIn("proc.wait(timeout=300)", section)
        self.assertIn("os.killpg", section)
        self.assertIn("start_new_session=True", section)

    def test_fresh_storage_and_hosted_scope_are_required(self):
        section = full_build_section(self.text)
        self.assertIn("tempfile.mkdtemp(", section)
        self.assertIn('os.environ["RUNNER_TEMP"]', section)
        self.assertIn('"github-hosted"', section)
        self.assertIn("needs: runtime-safety", section)
        self.assertIn("github.event_name == 'push'", section)
        self.assertIn("refs/heads/dev/reqsys-e2e-redmine-6.1.4-20260928", section)

    def test_no_external_secret_or_deploy_is_added(self):
        section = full_build_section(self.text)
        self.assertNotIn("${{ secrets.", section)
        self.assertNotIn("trigger_deploy", section)
        self.assertNotIn("continue-on-error", section)
        self.assertNotIn("security-events: write", section)
        self.assertIn("persist-credentials: false", section)
        self.assertIn('key = secrets.token_hex(20)', section)
        self.assertIn("env = {name: os.environ[name]", section)

    def test_persisted_effect_has_independent_readback(self):
        section = full_build_section(self.text)
        self.assertIn("SELECT project_id FROM issues WHERE id=?", section)
        self.assertIn("SELECT is_public FROM projects WHERE id=?", section)
        self.assertIn("?mode=ro", section)
        self.assertIn("CI_PERSISTED_ISSUE_MISMATCH", section)

    def test_actual_runtime_is_audited_even_after_build_failure(self):
        section = full_build_section(self.text)
        self.assertIn("if: always() && steps.build.outputs.root != ''", section)
        self.assertIn('target="${BUILD_ROOT}/.runtime/redmine-6.1.5"', section)
        self.assertIn("RUNTIME_AUDIT_BLOCKED_LOCK_NOT_GENERATED", section)
        self.assertIn("bundler-audit check --update", section)
        self.assertNotIn("--ignore", section)

    def test_missing_or_duplicate_job_is_rejected(self):
        with self.assertRaises(ValueError):
            full_build_section(self.text.split("\n  runtime-full-build:", 1)[0])
        with self.assertRaises(ValueError):
            full_build_section(self.text + "\n  runtime-full-build:\n")

    def test_no_artifact_storage_or_schedule_is_added(self):
        section = full_build_section(self.text)
        self.assertNotIn("upload-artifact", section)
        self.assertNotIn("schedule:", section)
        self.assertIn("cancel-in-progress: false", section)


if __name__ == "__main__":
    unittest.main()
