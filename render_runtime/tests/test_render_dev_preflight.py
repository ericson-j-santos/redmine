"""Controles locais de transporte; não representam autenticação real no Render."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from render_runtime import render_dev_preflight as pf

SHA = "a" * 40
TOKEN = "test-only-transport-token-not-real"
APP_KEY = "test-only-app-key-never-print"
SERVICE = {
    "id": pf.SERVICE, "name": pf.SERVICE_NAME, "ownerId": pf.OWNER,
    "repo": f"https://github.com/{pf.REPOSITORY}", "branch": pf.BRANCH,
    "type": "web_service", "autoDeploy": "no",
    "suspended": "not_suspended", "updatedAt": "2026-10-19T22:00:00Z",
    "serviceDetails": {
        "plan": "free", "runtime": "ruby",
        "url": f"https://{pf.SERVICE_NAME}.onrender.com",
        "envSpecificDetails": {
            "buildCommand": "bash render_runtime/build_redmine_6_1_4.sh",
            "startCommand": "cd .runtime/redmine-6.1.4 && bundle exec puma -b tcp://0.0.0.0:$PORT -e production",
        },
    },
}
VARS = [
    {"envVar": {"key": "REQSYS_REDMINE_API_KEY", "value": APP_KEY}, "cursor": "x"},
    {"envVar": {"key": "REQSYS_REDMINE_EPHEMERAL_E2E", "value": "1"}, "cursor": "y"},
]
ENV = {
    "GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted",
    "GITHUB_REPOSITORY": pf.REPOSITORY,
    "GITHUB_REF": f"refs/heads/{pf.BRANCH}", "GITHUB_EVENT_NAME": "push",
    "GITHUB_SHA": SHA, "RENDER_API_KEY": TOKEN,
}


class FakeClient:
    def __init__(self, after=None, variables=None):
        self.calls = []
        self.after = SERVICE if after is None else after
        self.variables = VARS if variables is None else variables

    def get(self, path):
        self.calls.append(path)
        if path == pf.ENV_PATH:
            return copy.deepcopy(self.variables)
        if path == pf.SERVICE_PATH:
            return copy.deepcopy(SERVICE if len(self.calls) == 1 else self.after)
        raise AssertionError("unexpected network target")


class Transport:
    def __init__(self, status=200, raw=b"{}"):
        self.status = status
        self.raw = raw
        self.calls = []
        self.closed = False
        self.reads = 0

    def request(self, method, path, headers):
        self.calls.append((method, path, headers))

    def getresponse(self):
        return self

    def read(self, length):
        self.reads += 1
        return self.raw[:length]

    def close(self):
        self.closed = True


class RenderPreflightTests(unittest.TestCase):
    def test_exact_commit_plan_is_not_executed(self):
        plan = pf.exact_deploy_plan(SHA)
        self.assertEqual(plan["body"], {"commitId": SHA, "clearCache": "do_not_clear"})
        self.assertEqual(plan["url"], f"https://api.render.com/v1/services/{pf.SERVICE}/deploys")
        self.assertIs(plan["executed"], False)

    def test_invalid_sha_cannot_make_request(self):
        for sha in ("main", "", "abc", "A" * 40, True, None, SHA + "\n"):
            with self.subTest(sha=sha):
                with self.assertRaisesRegex(pf.PreflightBlocked, "TARGET_SHA_INVALID"):
                    pf.exact_deploy_plan(sha)

    def test_readback_and_plan_do_not_authorize_discard_or_deploy(self):
        client = FakeClient()
        result = pf.qualify(SHA, TOKEN, client)
        self.assertEqual(client.calls, [pf.SERVICE_PATH, pf.ENV_PATH, pf.SERVICE_PATH])
        self.assertEqual(result["status"], "read_transport_verified")
        for name in ("deployment_ready", "data_discarded",
                     "data_preservation_verified", "post_transport_verified"):
            self.assertIs(result[name], False)
        self.assertEqual(result["deploy_plan"]["body"]["commitId"], SHA)
        text = json.dumps(result)
        self.assertNotIn(TOKEN, text)
        self.assertNotIn(APP_KEY, text)

    def test_readonly_replay_is_deterministic(self):
        self.assertEqual(pf.qualify(SHA, TOKEN, FakeClient()),
                         pf.qualify(SHA, TOKEN, FakeClient()))

    def test_wrong_service_workspace_branch_and_auto_deploy_rejected(self):
        for field, value in (("id", "srv-other"), ("ownerId", "tea-other"),
                             ("name", "redmine"), ("repo", "https://example.org"),
                             ("branch", "main"), ("autoDeploy", "yes"),
                             ("suspended", "suspended"), ("type", "cron_job")):
            with self.subTest(field=field):
                payload = copy.deepcopy(SERVICE)
                payload[field] = value
                with self.assertRaisesRegex(pf.PreflightBlocked, "IDENTITY_OR_STATE"):
                    pf.service_fingerprint(payload)

    def test_paid_plan_wrong_url_or_command_rejected(self):
        for field, value in (("plan", "starter"), ("runtime", "docker"),
                             ("url", "https://different.onrender.com")):
            with self.subTest(field=field):
                payload = copy.deepcopy(SERVICE)
                payload["serviceDetails"][field] = value
                with self.assertRaisesRegex(pf.PreflightBlocked, "CONFIGURATION"):
                    pf.service_fingerprint(payload)
        payload = copy.deepcopy(SERVICE)
        payload["serviceDetails"]["envSpecificDetails"]["buildCommand"] = "other"
        with self.assertRaisesRegex(pf.PreflightBlocked, "CONFIGURATION"):
            pf.service_fingerprint(payload)

    def test_service_drift_aborts_after_independent_read(self):
        after = copy.deepcopy(SERVICE)
        after["updatedAt"] = "2026-10-19T22:01:00Z"
        with self.assertRaisesRegex(pf.PreflightBlocked, "CHANGED_DURING"):
            pf.qualify(SHA, TOKEN, FakeClient(after=after))

    def test_empty_direct_variables_are_not_assumed_absent_in_groups(self):
        flags = pf.configuration_flags([])
        self.assertFalse(flags["api_key_reference_present"])
        self.assertFalse(flags["environment_groups_checked"])
        self.assertEqual(flags["scope"], "service_direct_variables_only")
        with self.assertRaisesRegex(pf.PreflightBlocked, "DIRECT_CONFIGURATION"):
            pf.qualify(SHA, TOKEN, FakeClient(variables=[]))

    def test_env_values_are_never_returned(self):
        text = json.dumps(pf.configuration_flags(VARS))
        self.assertNotIn(APP_KEY, text)
        self.assertIn("api_key_reference_present", text)

    def test_env_duplicate_partial_or_ambiguous_page_rejected(self):
        for value in ({}, VARS * 50, VARS + [VARS[0]], [{"key": "x"}],
                      [{"envVar": {"key": "REQSYS_REDMINE_API_KEY"}}]):
            with self.subTest(shape=type(value).__name__):
                with self.assertRaises(pf.PreflightBlocked):
                    pf.configuration_flags(value)

    def test_missing_secret_stops_before_network_and_is_not_success(self):
        env = dict(ENV, RENDER_API_KEY="")
        with patch.object(pf.http.client, "HTTPSConnection") as connection:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(pf.main(env), 2)
            connection.assert_not_called()
        receipt = json.loads(output.getvalue())
        self.assertEqual(receipt["blocker"], "RENDER_CREDENTIAL_NOT_AVAILABLE")
        self.assertFalse(receipt["deployment_requested"])
        self.assertFalse(receipt["data_discarded"])

    def test_invalid_execution_scope_stops_before_credentials_or_network(self):
        changes = [
            {"GITHUB_ACTIONS": "false"}, {"RUNNER_ENVIRONMENT": "self-hosted"},
            {"GITHUB_REPOSITORY": "other/repo"}, {"GITHUB_REF": "refs/heads/main"},
            {"GITHUB_EVENT_NAME": "pull_request"},
        ]
        for change in changes:
            with self.subTest(change=change), patch.object(pf, "qualify") as qualify:
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(pf.main(dict(ENV, **change)), 2)
                qualify.assert_not_called()
                self.assertEqual(json.loads(output.getvalue())["blocker"],
                                 "PREFLIGHT_EXECUTION_SCOPE_INVALID")

    def test_token_format_and_path_injection_rejected(self):
        for token in ("", "tiny", TOKEN + "\n", TOKEN + "\rX-Test:bad"):
            with self.subTest(token_length=len(token)):
                with self.assertRaises(pf.PreflightBlocked):
                    pf.RenderReadOnly(token)
        client = pf.RenderReadOnly(TOKEN)
        for path in ("https://other.example", pf.SERVICE_PATH + "/deploys",
                     pf.ENV_PATH + "&other=1", "/v1/services/another"):
            with self.subTest(path=path):
                with self.assertRaisesRegex(pf.PreflightBlocked, "PATH_NOT_ALLOWED"):
                    client.get(path)

    def test_https_get_is_fixed_and_closes_connection(self):
        transport = Transport(raw=json.dumps(SERVICE).encode())
        with patch.object(pf.http.client, "HTTPSConnection", return_value=transport) as ctor:
            result = pf.RenderReadOnly(TOKEN).get(pf.SERVICE_PATH)
        self.assertEqual(result, SERVICE)
        self.assertEqual(ctor.call_args.args, ("api.render.com",))
        self.assertEqual(ctor.call_args.kwargs["timeout"], 15)
        self.assertEqual(transport.calls[0][0], "GET")
        self.assertTrue(transport.closed)

    def test_http_error_body_never_read_printed_or_retried(self):
        for status in (301, 302, 307, 401, 403, 404, 429, 500):
            with self.subTest(status=status):
                transport = Transport(status=status, raw=(TOKEN + APP_KEY).encode())
                with patch.object(pf.http.client, "HTTPSConnection", return_value=transport):
                    with self.assertRaises(pf.PreflightBlocked) as error:
                        pf.RenderReadOnly(TOKEN).get(pf.SERVICE_PATH)
                self.assertNotIn(TOKEN, str(error.exception))
                self.assertNotIn(APP_KEY, str(error.exception))
                self.assertEqual(transport.reads, 0)
                self.assertEqual(len(transport.calls), 1)
                self.assertTrue(transport.closed)

    def test_bad_or_oversized_json_and_socket_errors_sanitized(self):
        for raw in (b"invalid:" + TOKEN.encode(), b"x" * (pf.MAX_BYTES + 1)):
            with self.subTest(length=len(raw)):
                transport = Transport(raw=raw)
                with patch.object(pf.http.client, "HTTPSConnection", return_value=transport):
                    with self.assertRaises(pf.PreflightBlocked) as error:
                        pf.RenderReadOnly(TOKEN).get(pf.SERVICE_PATH)
                self.assertNotIn(TOKEN, str(error.exception))
                self.assertTrue(transport.closed)
        transport = Transport()
        with patch.object(pf.http.client, "HTTPSConnection", return_value=transport), \
                patch.object(transport, "request", side_effect=OSError(TOKEN)):
            with self.assertRaisesRegex(pf.PreflightBlocked, "READ_OR_JSON_FAILED"):
                pf.RenderReadOnly(TOKEN).get(pf.SERVICE_PATH)
        self.assertTrue(transport.closed)

    def test_main_success_still_reports_no_deployment(self):
        with patch.object(pf, "RenderReadOnly", return_value=FakeClient()):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(pf.main(ENV), 0)
        receipt = json.loads(output.getvalue())
        self.assertFalse(receipt["deployment_ready"])
        self.assertFalse(receipt["deployment_requested"])
        self.assertEqual(receipt["executor_sha"], SHA)

    def test_workflow_is_nonrecurring_restricted_and_secret_is_step_scoped(self):
        source = (Path(__file__).resolve().parents[2]
                  / ".github/workflows/render-dev-preflight.yml").read_text()
        self.assertIn("paths:", source)
        self.assertIn("branches: [dev/reqsys-e2e-redmine-6.1.4-20260928]", source)
        self.assertIn("contents: read", source)
        self.assertIn("persist-credentials: false", source)
        self.assertIn("cancel-in-progress: false", source)
        self.assertNotIn("schedule:", source)
        self.assertNotIn("pull_request", source)
        self.assertNotIn("continue-on-error", source)
        self.assertNotIn("artifacts", source)
        self.assertEqual(source.count("${{ secrets.RENDER_API_KEY }}"), 1)
        validation, qualification = source.split("- name: Qualify existing Render access", 1)
        self.assertNotIn("RENDER_API_KEY", validation)
        self.assertIn("env:", qualification)
        self.assertIn("python3 render_runtime/render_dev_preflight.py", qualification)


if __name__ == "__main__":
    unittest.main()
