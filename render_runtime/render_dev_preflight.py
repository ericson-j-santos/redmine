"""Preflight Render somente leitura; não publica nem descarta dados."""
from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import ssl
from collections.abc import Mapping

REPOSITORY = "ericson-j-santos/redmine"
BRANCH = "dev/reqsys-e2e-redmine-6.1.4-20260928"
SERVICE = "srv-dathlk2d0e5s73c5722g"
OWNER = "tea-csp943bgbbvc73f20f5g"
SERVICE_NAME = "redmine-reqsys-e2e-dev-614"
SERVICE_PATH = f"/v1/services/{SERVICE}"
ENV_PATH = f"{SERVICE_PATH}/env-vars?limit=100"
ALLOWED_READS = frozenset({SERVICE_PATH, ENV_PATH})
MAX_BYTES = 65536


class PreflightBlocked(ValueError):
    """Código estável; nunca incorpora corpo HTTP, token ou exceção remota."""


def exact_deploy_plan(sha: str) -> dict:
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise PreflightBlocked("TARGET_SHA_INVALID")
    return {
        "method": "POST",
        "url": f"https://api.render.com{SERVICE_PATH}/deploys",
        "body": {"commitId": sha, "clearCache": "do_not_clear"},
        "executed": False,
    }


class RenderReadOnly:
    """HTTPS direto, GET allowlisted, sem redirects, proxies ou retentativas."""

    def __init__(self, token: str):
        if not isinstance(token, str) or not token:
            raise PreflightBlocked("RENDER_CREDENTIAL_NOT_AVAILABLE")
        if not re.fullmatch(r"[\x21-\x7e]{20,4096}", token):
            raise PreflightBlocked("RENDER_CREDENTIAL_FORMAT_INVALID")
        self._token = token

    def get(self, path: str):
        if path not in ALLOWED_READS:
            raise PreflightBlocked("RENDER_PATH_NOT_ALLOWED")
        conn = http.client.HTTPSConnection(
            "api.render.com", timeout=15, context=ssl.create_default_context()
        )
        try:
            conn.request("GET", path, headers={
                "Authorization": "Bearer " + self._token,
                "Accept": "application/json",
                "User-Agent": "reqsys-redmine-dev-readonly-preflight/1",
            })
            response = conn.getresponse()
            # Do not read or emit error bodies; redirects are never followed.
            if response.status != 200:
                if response.status in (401, 403):
                    raise PreflightBlocked("RENDER_AUTHORIZATION_REJECTED")
                if 300 <= response.status < 400:
                    raise PreflightBlocked("RENDER_REDIRECT_REJECTED")
                raise PreflightBlocked("RENDER_HTTP_READ_FAILED")
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise PreflightBlocked("RENDER_RESPONSE_TOO_LARGE")
            return json.loads(raw)
        except PreflightBlocked:
            raise
        except (OSError, ValueError, http.client.HTTPException):
            raise PreflightBlocked("RENDER_READ_OR_JSON_FAILED") from None
        finally:
            conn.close()


def service_fingerprint(payload) -> str:
    if not isinstance(payload, dict):
        raise PreflightBlocked("RENDER_SERVICE_SCHEMA_INVALID")
    expected = {
        "id": SERVICE, "name": SERVICE_NAME, "ownerId": OWNER,
        "repo": f"https://github.com/{REPOSITORY}", "branch": BRANCH,
        "type": "web_service", "autoDeploy": "no",
        "suspended": "not_suspended",
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        raise PreflightBlocked("RENDER_SERVICE_IDENTITY_OR_STATE_MISMATCH")
    details = payload.get("serviceDetails")
    if not isinstance(details, dict):
        raise PreflightBlocked("RENDER_SERVICE_SCHEMA_INVALID")
    runtime = details.get("envSpecificDetails")
    if not isinstance(runtime, dict):
        raise PreflightBlocked("RENDER_SERVICE_SCHEMA_INVALID")
    if (details.get("plan") != "free" or details.get("runtime") != "ruby"
            or details.get("url") != f"https://{SERVICE_NAME}.onrender.com"
            or runtime.get("buildCommand") != "bash render_runtime/build_redmine_6_1_4.sh"
            or runtime.get("startCommand") !=
            "cd .runtime/redmine-6.1.4 && bundle exec puma -b tcp://0.0.0.0:$PORT -e production"
            or not isinstance(payload.get("updatedAt"), str)):
        raise PreflightBlocked("RENDER_SERVICE_CONFIGURATION_MISMATCH")
    # Full metadata digest detects changes beyond the selected identity fields.
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()


def configuration_flags(payload) -> dict:
    # The endpoint exposes direct variables, not linked environment groups.
    # Never return values or claim missing variables in groups are absent.
    if not isinstance(payload, list) or len(payload) >= 100:
        raise PreflightBlocked("RENDER_ENV_SCHEMA_OR_PAGINATION_UNCONFIRMED")
    selected = {}
    wanted = {"REQSYS_REDMINE_API_KEY", "REQSYS_REDMINE_EPHEMERAL_E2E"}
    seen = set()
    for item in payload:
        variable = item.get("envVar") if isinstance(item, dict) else None
        if not isinstance(variable, dict) or not isinstance(variable.get("key"), str):
            raise PreflightBlocked("RENDER_ENV_SCHEMA_OR_PAGINATION_UNCONFIRMED")
        name = variable["key"]
        if name in seen:
            raise PreflightBlocked("RENDER_ENV_DUPLICATE")
        seen.add(name)
        if name in wanted:
            value = variable.get("value")
            if not isinstance(value, str):
                raise PreflightBlocked("RENDER_ENV_VALUE_UNCONFIRMED")
            selected[name] = value
    return {
        "api_key_reference_present": bool(selected.get("REQSYS_REDMINE_API_KEY", "").strip()),
        "ephemeral_flag_matches": selected.get("REQSYS_REDMINE_EPHEMERAL_E2E") == "1",
        "scope": "service_direct_variables_only",
        "environment_groups_checked": False,
    }


def qualify(sha: str, token: str, client=None) -> dict:
    plan = exact_deploy_plan(sha)
    client = client if client is not None else RenderReadOnly(token)
    before = service_fingerprint(client.get(SERVICE_PATH))
    flags = configuration_flags(client.get(ENV_PATH))
    after = service_fingerprint(client.get(SERVICE_PATH))
    if before != after:
        raise PreflightBlocked("RENDER_SERVICE_CHANGED_DURING_PREFLIGHT")
    if not flags["api_key_reference_present"] or not flags["ephemeral_flag_matches"]:
        raise PreflightBlocked("RENDER_DIRECT_CONFIGURATION_UNCONFIRMED")
    return {
        "status": "read_transport_verified",
        "service_id": SERVICE, "repository": REPOSITORY,
        "target_sha": sha, "service_metadata_sha256": after,
        "configuration": flags, "deploy_plan": plan,
        "deployment_ready": False, "data_discarded": False,
        "data_preservation_verified": False, "post_transport_verified": False,
        "remaining_gates": ["preservation_or_conditional_discard_evidence",
                            "current_sha_ci_and_deploy_authorization",
                            "controlled_post_and_independent_deploy_readback",
                            "published_runtime_e2e"],
    }


def main(environ: Mapping[str, str] | None = None) -> int:
    env = os.environ if environ is None else environ
    receipt = {"service_id": SERVICE, "scope": "read_only_preflight_not_deploy",
               "deployment_ready": False, "deployment_requested": False,
               "data_discarded": False}
    try:
        if (env.get("GITHUB_ACTIONS") != "true"
                or env.get("RUNNER_ENVIRONMENT") != "github-hosted"
                or env.get("GITHUB_REPOSITORY") != REPOSITORY
                or env.get("GITHUB_REF") != f"refs/heads/{BRANCH}"
                or env.get("GITHUB_EVENT_NAME") != "push"):
            raise PreflightBlocked("PREFLIGHT_EXECUTION_SCOPE_INVALID")
        sha = env.get("GITHUB_SHA", "")
        exact_deploy_plan(sha)
        receipt["executor_sha"] = sha
        receipt.update(qualify(sha, env.get("RENDER_API_KEY", "")))
    except PreflightBlocked as exc:
        receipt.update(status="blocked", blocker=str(exc))
        print(json.dumps(receipt, sort_keys=True))
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
