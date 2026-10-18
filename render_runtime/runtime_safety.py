#!/usr/bin/env python3
"""Proteções do build DEV descartável; não migra nem apaga dados existentes."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

PROJECT_DEFAULT = "reqsys-e2e-dev"
MAX_RESPONSE_BYTES = 65536


class SafetyError(ValueError):
    """Erro estável e sanitizado; nunca inclui chave ou corpo de resposta."""


def project_identifier(env: dict[str, str]) -> str:
    value = env.get("REQSYS_REDMINE_PROJECT_IDENTIFIER", PROJECT_DEFAULT)
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,99}", value):
        raise SafetyError("REDMINE_PROJECT_IDENTIFIER_INVALID")
    return value


def api_key(env: dict[str, str]) -> str:
    value = env.get("REQSYS_REDMINE_API_KEY", "")
    if not re.fullmatch(r"[a-fA-F0-9]{40}", value):
        raise SafetyError("REDMINE_API_KEY_REFERENCE_INVALID")
    return value


def reserve_runtime(root: Path, env: dict[str, str]) -> Path:
    """Reserva exclusiva por mkdir; repetição/concorrência nunca sobrescrevem."""
    if env.get("REQSYS_REDMINE_EPHEMERAL_E2E") != "1":
        raise SafetyError("REDMINE_EPHEMERAL_SCOPE_NOT_CONFIRMED")
    api_key(env)
    project_identifier(env)
    root = Path(root)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise SafetyError("REDMINE_BUILD_ROOT_INVALID")
    runtime = root / ".runtime"
    try:
        runtime.mkdir(mode=0o700)
    except FileExistsError:
        raise SafetyError("REDMINE_RUNTIME_EXISTS_PRESERVED") from None
    except OSError:
        raise SafetyError("REDMINE_RUNTIME_RESERVATION_FAILED") from None
    return runtime


def project_id(payload: object, identifier: str) -> int:
    """Valida identidade exata, ID real positivo e projeto privado."""
    if not isinstance(payload, dict) or not isinstance(payload.get("project"), dict):
        raise SafetyError("REDMINE_PROJECT_RESPONSE_INVALID")
    project = payload["project"]
    value = project.get("id")
    if type(value) is not int or value <= 0:
        raise SafetyError("REDMINE_PROJECT_ID_INVALID")
    if project.get("identifier") != identifier:
        raise SafetyError("REDMINE_PROJECT_IDENTITY_MISMATCH")
    if project.get("is_public") is not False:
        raise SafetyError("REDMINE_PROJECT_NOT_PRIVATE")
    return value


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def resolve_project(env: dict[str, str]) -> int:
    """GET real somente no Puma loopback; sem proxies, redirects ou logs brutos."""
    identifier = project_identifier(env)
    key = api_key(env)
    url = env.get("REDMINE_BASE_URL", "")
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        raise SafetyError("REDMINE_LOOPBACK_URL_INVALID") from None
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query or parsed.fragment
        or port is None or not 1 <= port <= 65535
    ):
        raise SafetyError("REDMINE_LOOPBACK_URL_INVALID")
    request = Request(
        f"http://127.0.0.1:{port}/projects/{identifier}.json",
        headers={"X-Redmine-API-Key": key, "Accept": "application/json"},
        method="GET",
    )
    try:
        opener = build_opener(ProxyHandler({}), NoRedirect())
        with opener.open(request, timeout=10) as response:
            if response.status != 200:
                raise SafetyError("REDMINE_PROJECT_HTTP_STATUS_INVALID")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        exc.close()
        raise SafetyError("REDMINE_PROJECT_LOOKUP_FAILED") from None
    except (URLError, TimeoutError, OSError):
        raise SafetyError("REDMINE_PROJECT_LOOKUP_FAILED") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise SafetyError("REDMINE_PROJECT_RESPONSE_TOO_LARGE")
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError):
        raise SafetyError("REDMINE_PROJECT_RESPONSE_INVALID") from None
    return project_id(payload, identifier)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("reserve", "project"))
    args = parser.parse_args(argv)
    try:
        if args.action == "reserve":
            reserve_runtime(Path(__file__).resolve().parents[1], dict(os.environ))
            print("REDMINE_BUILD_RESERVED")
        else:
            print(resolve_project(dict(os.environ)))
    except SafetyError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
