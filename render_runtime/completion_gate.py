"""Validação estrita de suites reais: zero falhas, erros ou testes pulados."""
from __future__ import annotations

import re


class CompletionGateError(ValueError):
    """A evidência de execução completa não foi comprovada."""


def require_complete_suites(texts: dict[str, str]) -> dict[str, dict[str, int]]:
    """Verifica os resumos de Attachment/Mailer sem executar ou simular testes."""
    if set(texts) != {"attachment", "mailer"}:
        raise CompletionGateError("COMPLETE_SUITES_REQUIRED")
    results = {}
    for name, text in texts.items():
        if not isinstance(text, str) or len(text) > 2_000_000:
            raise CompletionGateError("COMPLETE_SUITE_LOG_INVALID")
        matches = re.findall(
            r"(?m)^\s*(\d+) runs, (\d+) assertions, (\d+) failures, "
            r"(\d+) errors, (\d+) skips\s*$",
            text,
        )
        if len(matches) != 1:
            raise CompletionGateError("COMPLETE_SUITE_SUMMARY_AMBIGUOUS")
        summary = dict(zip(
            ("runs", "assertions", "failures", "errors", "skips"),
            map(int, matches[0]),
        ))
        if (summary["runs"] < 5 or summary["assertions"] < 5
                or summary["failures"] or summary["errors"] or summary["skips"]):
            raise CompletionGateError("COMPLETE_SUITE_NOT_PASSED")
        results[name] = summary
    return results
