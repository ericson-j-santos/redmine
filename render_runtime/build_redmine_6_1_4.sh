#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

# The old entrypoint/start path is retained for the existing Render DEV service.
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
export PYTHONDONTWRITEBYTECODE=1
REDMINE_VERSION="6.1.5"
EXPECTED_SHA256="4b653d8863c012fdb226aedf6f8a18bdfa08d04625d15e8aafbbc3c4f6b70144"
REQSYS_SHA="9be16bfee3a3b8f9e3478e197e77d9231cdc4be6"
HARNESS_SOURCE_SHA="b84576f76fad584bc420cb447d046aaafdc775ba"
HARNESS_BLOB_SHA="4008741f26abc4a1487978682ad53d17b9f20adc"
RUNTIME_ROOT="${ROOT}/.runtime"
REDMINE_ROOT="${RUNTIME_ROOT}/redmine-${REDMINE_VERSION}"
LEGACY_START_DIR="${RUNTIME_ROOT}/redmine-6.1.4"
REQSYS_ROOT="${RUNTIME_ROOT}/reqsys-${REQSYS_SHA}"
REQSYS_VENV="${RUNTIME_ROOT}/reqsys-e2e-venv"
ARCHIVE="${RUNTIME_ROOT}/redmine-${REDMINE_VERSION}.tar.gz"
STAGE="preflight"
E2E_PUMA_PID=""

cleanup() {
  if [[ -n "${E2E_PUMA_PID}" ]]; then
    kill "${E2E_PUMA_PID}" >/dev/null 2>&1 || true
    wait "${E2E_PUMA_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT
trap 'code=$?; printf "REDMINE_BUILD_FAILED stage=%s code=%s\n" "${STAGE}" "${code}" >&2; exit "${code}"' ERR

# Fail before download, bootstrap or data writes unless the isolated disposable
# scope is explicitly configured. Atomic mkdir refuses ALL existing .runtime
# entries, including symlinks; failed/repeated builds preserve their evidence.
REQSYS_REDMINE_SOURCE_IDENTITY="$(python3 "${ROOT}/render_runtime/release_identity.py" capture)"
export REQSYS_REDMINE_SOURCE_IDENTITY
python3 "${ROOT}/render_runtime/runtime_safety.py" reserve

STAGE="download"
curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
  --connect-timeout 10 --max-time 90 --retry 2 --retry-delay 2 \
  "https://www.redmine.org/releases/redmine-${REDMINE_VERSION}.tar.gz" \
  --output "${ARCHIVE}"
printf '%s  %s\n' "${EXPECTED_SHA256}" "${ARCHIVE}" | sha256sum --check -
tar -xzf "${ARCHIVE}" -C "${RUNTIME_ROOT}"

STAGE="reqsys_checkout"
mkdir "${REQSYS_ROOT}"
git -C "${REQSYS_ROOT}" init -q
git -C "${REQSYS_ROOT}" remote add origin "https://github.com/ericson-j-santos/reqsys-v2-enterprise-real.git"
git -C "${REQSYS_ROOT}" fetch -q --depth=1 origin "${REQSYS_SHA}" "${HARNESS_SOURCE_SHA}"
git -C "${REQSYS_ROOT}" checkout -q --detach "${REQSYS_SHA}"
test "$(git -C "${REQSYS_ROOT}" rev-parse HEAD)" = "${REQSYS_SHA}"

# Current product code does not contain this test harness. Import only the
# reviewed immutable harness, not the old product tree; record both identities.
HARNESS_PATH="${REQSYS_ROOT}/scripts/redmine_lifecycle_real_e2e.py"
test ! -e "${HARNESS_PATH}"
test "$(git -C "${REQSYS_ROOT}" rev-parse "${HARNESS_SOURCE_SHA}:scripts/redmine_lifecycle_real_e2e.py")" = "${HARNESS_BLOB_SHA}"
git -C "${REQSYS_ROOT}" show "${HARNESS_SOURCE_SHA}:scripts/redmine_lifecycle_real_e2e.py" > "${HARNESS_PATH}"
test "$(git -C "${REQSYS_ROOT}" hash-object "${HARNESS_PATH}")" = "${HARNESS_BLOB_SHA}"

STAGE="dependency_pins"
python3 "${ROOT}/render_runtime/security_dependencies.py" patch

STAGE="ruby_dependencies"
cp "${ROOT}/render_runtime/database.yml" "${REDMINE_ROOT}/config/database.yml"
cd "${REDMINE_ROOT}"
bundle config unset deployment || true
bundle config unset frozen || true
bundle config set --local without 'development'
BUNDLE_DEPLOYMENT=false BUNDLE_FROZEN=false bundle lock
BUNDLE_DEPLOYMENT=false BUNDLE_FROZEN=false bundle install --jobs 4 --retry 3
STAGE="isolated_bootstrap"
RAILS_ENV=production bundle exec rake generate_secret_token
RAILS_ENV=production bundle exec rails db:migrate
# The archive checksum fixes the source before setup. Version observation needs
# the initialized Rails application, not a standalone require of redmine/version.
STAGE="version_observation"
OBSERVED_REDMINE_VERSION="$(RAILS_ENV=production bundle exec rails runner 'print Redmine::VERSION.to_s')"
case "${OBSERVED_REDMINE_VERSION}" in
  "${REDMINE_VERSION}"|"${REDMINE_VERSION}.stable") ;;
  *) echo "REDMINE_OBSERVED_VERSION_MISMATCH" >&2; exit 2 ;;
esac
printf 'REDMINE_VERSION_OBSERVED version=%s\n' "${OBSERVED_REDMINE_VERSION}"

STAGE="isolated_bootstrap"
RAILS_ENV=production REDMINE_LANG=en bundle exec rake redmine:load_default_data
RAILS_ENV=production bundle exec rails runner "${ROOT}/render_runtime/bootstrap.rb"
RAILS_ENV=production bundle exec rake assets:precompile


# Dependency compatibility is exercised in a separate disposable test database.
# Both upstream suites must actually run; their summaries and loaded versions
# are checked independently by Python. Mailer uses Rails' test delivery adapter.
STAGE="dependency_audit"
bundle exec bundle audit check --update
STAGE="dependency_compatibility"
RAILS_ENV=test bundle exec rake db:schema:load
RAILS_ENV=test bundle exec ruby -Itest test/unit/attachment_test.rb \
  | tee tmp/reqsys-attachment-compat.log
RAILS_ENV=test bundle exec ruby -Itest test/unit/mailer_test.rb \
  | tee tmp/reqsys-mailer-compat.log
bundle exec ruby -rjson -rmail -rzip -rsqlite3 \
  -e 'puts JSON.generate(%w[mail rubyzip sqlite3].to_h { |n| [n, Gem.loaded_specs.fetch(n).version.to_s] })' \
  > tmp/reqsys-loaded-gems.json
python3 "${ROOT}/render_runtime/security_dependencies.py" verify-compatibility

STAGE="python_dependencies"
python3 -m venv "${REQSYS_VENV}"
"${REQSYS_VENV}/bin/python" -m pip install --disable-pip-version-check -q \
  "sqlalchemy==2.0.41" "pydantic==2.13.4" "pydantic-settings==2.7.1"

STAGE="puma_readiness"
E2E_PORT="3000"
RAILS_ENV=production bundle exec puma -w 0 -b "tcp://127.0.0.1:${E2E_PORT}" -e production \
  > "${RUNTIME_ROOT}/reqsys-redmine-e2e-puma.log" 2>&1 &
E2E_PUMA_PID="$!"
ready="false"
for _attempt in $(seq 1 30); do
  kill -0 "${E2E_PUMA_PID}"
  if curl --fail --silent --show-error --connect-timeout 1 --max-time 2 \
    "http://127.0.0.1:${E2E_PORT}/" >/dev/null; then
    ready="true"
    break
  fi
  sleep 1
done
test "${ready}" = "true"

STAGE="project_identity"
export APP_ENV="development"
export DATABASE_URL="sqlite:///${RUNTIME_ROOT}/reqsys-e2e.sqlite3"
export REDMINE_BASE_URL="http://127.0.0.1:${E2E_PORT}"
export REDMINE_API_KEY="${REQSYS_REDMINE_API_KEY}"
REDMINE_PROJECT_ID="$(python3 "${ROOT}/render_runtime/runtime_safety.py" project)"
export REDMINE_PROJECT_ID
export REDMINE_VERSION="${OBSERVED_REDMINE_VERSION}"
export REQSYS_E2E_SHA="${REQSYS_SHA}"
export REQSYS_E2E_HARNESS_SHA="${HARNESS_SOURCE_SHA}"
export REQSYS_E2E_HARNESS_BLOB="${HARNESS_BLOB_SHA}"
export PYTHONPATH="${REQSYS_ROOT}/backend:${REQSYS_ROOT}"
export PYTHONNOUSERSITE=1
unset PYTHONOPTIMIZE  # The reviewed harness uses assertions as validation gates.

STAGE="lifecycle_e2e"
(
  cd "${REQSYS_ROOT}"
  "${REQSYS_VENV}/bin/python" scripts/redmine_lifecycle_real_e2e.py
)

STAGE="evidence_validation"
EVIDENCE_SRC="${REQSYS_ROOT}/artifacts/redmine-e2e/evidence.json"
EVIDENCE_DST="${REDMINE_ROOT}/public/reqsys-e2e/evidence.json"
"${REQSYS_VENV}/bin/python" - "${EVIDENCE_SRC}" "${EVIDENCE_DST}" <<'PY'
import json
import os
import sys
from pathlib import Path

source, target = map(Path, sys.argv[1:])
raw = source.read_text(encoding="utf-8")
key = os.environ["REQSYS_REDMINE_API_KEY"]
if key in raw:
    raise SystemExit("E2E_SECRET_DETECTED")
payload = json.loads(raw)
if payload.get("status") != "passed" or payload.get("secret_values_in_evidence") is not False:
    raise SystemExit("E2E_EVIDENCE_NOT_PASSED")
if payload.get("reqsys_sha") != os.environ["REQSYS_E2E_SHA"]:
    raise SystemExit("E2E_REQSYS_SHA_MISMATCH")
redmine = payload.get("redmine", {})
if redmine.get("version") != os.environ["REDMINE_VERSION"]:
    raise SystemExit("E2E_REDMINE_VERSION_MISMATCH")
if redmine.get("project_id") != int(os.environ["REDMINE_PROJECT_ID"]):
    raise SystemExit("E2E_PROJECT_MISMATCH")
positive = payload.get("positive", {})
negative = payload.get("negative", {})
if not all(positive.get(name) is True for name in (
    "get_journals", "put_and_independent_readback", "remote_state_imported", "journal_imported"
)):
    raise SystemExit("E2E_POSITIVE_PROOF_MISSING")
if any(type(positive.get(name)) is not int or positive[name] != 0 for name in (
    "replay_mutation_count", "replay_audit_delta"
)):
    raise SystemExit("E2E_REPLAY_PROOF_INVALID")
if negative.get("quarantined") is not True or negative.get("control_rows") != 1:
    raise SystemExit("E2E_NEGATIVE_PROOF_MISSING")
if not isinstance(payload.get("correlation_id"), str) or not payload["correlation_id"]:
    raise SystemExit("E2E_CORRELATION_MISSING")
payload["test_harness"] = {
    "source_sha": os.environ["REQSYS_E2E_HARNESS_SHA"],
    "blob_sha": os.environ["REQSYS_E2E_HARNESS_BLOB"],
}
payload["evidence_scope"] = "isolated_build_not_post_deploy_or_pc24x7"
payload["source_identity"] = json.loads(os.environ["REQSYS_REDMINE_SOURCE_IDENTITY"])
payload["redmine_repo_sha"] = payload["source_identity"]["source_sha"]
serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
if key in serialized:
    raise SystemExit("E2E_SECRET_DETECTED")
target.parent.mkdir(parents=True, exist_ok=True)
with target.open("x", encoding="utf-8") as output:
    output.write(serialized)
if json.loads(target.read_text(encoding="utf-8")) != payload:
    raise SystemExit("E2E_EVIDENCE_READBACK_FAILED")
PY

python3 "${ROOT}/render_runtime/security_dependencies.py" verify-compatibility

STAGE="release_manifest"
python3 "${ROOT}/render_runtime/release_identity.py" publish

STAGE="legacy_start_compatibility"
# Relative alias created only after gates pass. No existing directory is replaced.
ln -sT "redmine-6.1.5" "${LEGACY_START_DIR}"
test "$(readlink -f "${LEGACY_START_DIR}")" = "${REDMINE_ROOT}"
echo "REQSYS_REDMINE_REAL_E2E_OK reqsys_sha=${REQSYS_SHA} harness_sha=${HARNESS_SOURCE_SHA}"
echo "REDMINE_RUNTIME_BUILD_OK version=${REDMINE_VERSION}"
