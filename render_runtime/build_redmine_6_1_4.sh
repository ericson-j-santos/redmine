#!/usr/bin/env bash
set -euo pipefail

REDMINE_VERSION="6.1.4"
ARCHIVE="redmine-${REDMINE_VERSION}.tar.gz"
URL="https://www.redmine.org/releases/${ARCHIVE}"
EXPECTED_SHA256="add3a006d37ef3d77a7ca0fe0907a2744b58831a349cb09a675442c2d2e82fc9"
ROOT="$(pwd)"
RUNTIME_ROOT="${ROOT}/.runtime"
REDMINE_ROOT="${RUNTIME_ROOT}/redmine-${REDMINE_VERSION}"

rm -rf "${RUNTIME_ROOT}"
mkdir -p "${RUNTIME_ROOT}"
curl --fail --silent --show-error --location "${URL}" --output "/tmp/${ARCHIVE}"
printf '%s  %s\n' "${EXPECTED_SHA256}" "/tmp/${ARCHIVE}" | sha256sum --check -
tar -xzf "/tmp/${ARCHIVE}" -C "${RUNTIME_ROOT}"

cp "${ROOT}/render_runtime/database.yml" "${REDMINE_ROOT}/config/database.yml"
cd "${REDMINE_ROOT}"

bundle config unset deployment || true
bundle config unset frozen || true
bundle config set --local without 'development'
BUNDLE_DEPLOYMENT=false BUNDLE_FROZEN=false bundle lock
BUNDLE_DEPLOYMENT=false BUNDLE_FROZEN=false bundle install --jobs 4 --retry 3
RAILS_ENV=production bundle exec rake generate_secret_token
RAILS_ENV=production bundle exec rails db:migrate
RAILS_ENV=production REDMINE_LANG=en bundle exec rake redmine:load_default_data
RAILS_ENV=production bundle exec rails runner "${ROOT}/render_runtime/bootstrap.rb"
RAILS_ENV=production bundle exec rake assets:precompile

# E2E real ReqSys <-> Redmine no mesmo ambiente: o segredo permanece local.
REQSYS_SHA="a3fe46286b31630aaef1be9ba6d5fddc783b9d61"
REQSYS_ROOT="${RUNTIME_ROOT}/reqsys-${REQSYS_SHA}"
REQSYS_VENV="${RUNTIME_ROOT}/reqsys-e2e-venv"
E2E_PORT="3000"

rm -rf "${REQSYS_ROOT}" "${REQSYS_VENV}"
mkdir -p "${REQSYS_ROOT}"
git -C "${REQSYS_ROOT}" init -q
git -C "${REQSYS_ROOT}" remote add origin "https://github.com/ericson-j-santos/reqsys-v2-enterprise-real.git"
git -C "${REQSYS_ROOT}" fetch -q --depth=1 origin "${REQSYS_SHA}"
git -C "${REQSYS_ROOT}" checkout -q --detach FETCH_HEAD
ACTUAL_REQSYS_SHA="$(git -C "${REQSYS_ROOT}" rev-parse HEAD)"
test "${ACTUAL_REQSYS_SHA}" = "${REQSYS_SHA}"

python3 -m venv "${REQSYS_VENV}"
"${REQSYS_VENV}/bin/python" -m pip install --disable-pip-version-check -q \
  "sqlalchemy==2.0.41" \
  "pydantic==2.13.4" \
  "pydantic-settings==2.7.1"

RAILS_ENV=production bundle exec puma -w 0 -b "tcp://127.0.0.1:${E2E_PORT}" -e production \
  > /tmp/reqsys-redmine-e2e-puma.log 2>&1 &
E2E_PUMA_PID="$!"
cleanup_e2e_puma() {
  kill "${E2E_PUMA_PID}" >/dev/null 2>&1 || true
  wait "${E2E_PUMA_PID}" >/dev/null 2>&1 || true
}
trap cleanup_e2e_puma EXIT

ready="false"
for _attempt in $(seq 1 30); do
  if curl --fail --silent --show-error "http://127.0.0.1:${E2E_PORT}/" >/dev/null; then
    ready="true"
    break
  fi
  sleep 1
done
test "${ready}" = "true"

export APP_ENV="development"
export DATABASE_URL="sqlite:////tmp/reqsys_redmine_e2e.sqlite3"
export REDMINE_BASE_URL="http://127.0.0.1:${E2E_PORT}"
export REDMINE_API_KEY="${REQSYS_REDMINE_API_KEY}"
export REDMINE_PROJECT_ID="1"
export REDMINE_VERSION="6.1.4.stable"
export REQSYS_E2E_SHA="${REQSYS_SHA}"
export PYTHONPATH="${REQSYS_ROOT}/backend:${REQSYS_ROOT}"

(
  cd "${REQSYS_ROOT}"
  "${REQSYS_VENV}/bin/python" scripts/redmine_lifecycle_real_e2e.py
)

EVIDENCE_SRC="${REQSYS_ROOT}/artifacts/redmine-e2e/evidence.json"
EVIDENCE_DST="${REDMINE_ROOT}/public/reqsys-e2e/evidence.json"
test -s "${EVIDENCE_SRC}"
mkdir -p "$(dirname "${EVIDENCE_DST}")"
cp "${EVIDENCE_SRC}" "${EVIDENCE_DST}"

"${REQSYS_VENV}/bin/python" - "${EVIDENCE_DST}" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
if payload.get("status") != "passed":
    raise SystemExit("e2e_evidence_not_passed")
if payload.get("secret_values_in_evidence") is not False:
    raise SystemExit("e2e_secret_contract_invalid")
payload["redmine"]["public_base_url"] = os.getenv(
    "RENDER_EXTERNAL_URL",
    "https://redmine-reqsys-e2e-dev-614.onrender.com",
)
path.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY

cleanup_e2e_puma
trap - EXIT

echo "REQSYS_REDMINE_REAL_E2E_OK reqsys_sha=${REQSYS_SHA}"
echo "REDMINE_RUNTIME_BUILD_OK version=${REDMINE_VERSION}"
