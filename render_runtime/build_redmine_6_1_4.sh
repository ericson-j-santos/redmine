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
bundle config set --local without 'development test'
BUNDLE_DEPLOYMENT=false BUNDLE_FROZEN=false bundle lock
BUNDLE_DEPLOYMENT=false BUNDLE_FROZEN=false bundle install --jobs 4 --retry 3
RAILS_ENV=production bundle exec rake generate_secret_token
RAILS_ENV=production bundle exec rails db:migrate
RAILS_ENV=production REDMINE_LANG=en bundle exec rake redmine:load_default_data
RAILS_ENV=production bundle exec rails runner "${ROOT}/render_runtime/bootstrap.rb"
RAILS_ENV=production bundle exec rake assets:precompile

echo "REDMINE_RUNTIME_BUILD_OK version=${REDMINE_VERSION}"
