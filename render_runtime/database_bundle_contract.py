"""Contrato aditivo do bundle de testes; não resolve nem escreve lockfiles."""
from __future__ import annotations

import hashlib
import re

SOURCE_GEMFILE_BLOB = "78b9c6651d531e8184adaa78c5369783a433be6c"
SOURCE_LOCK_BLOB = "41ac12fcfa7632e300e036e59d77d75c1c421f2b"
OBSERVER_MARKER = b"group :test do\n  gem 'observer', '0.1.2', require: false\n"
MYSQL_DECLARATION = b"gem 'mysql2', '~> 0.5.0', **(mysql_adapter ? {} : {group: :test, require: false})\n"
DATABASE_DECLARATIONS = b"# Declare each driver once, loading only configured adapters by default.\ngem 'mysql2', '~> 0.5.0', **(mysql_adapter ? {} : {group: :test, require: false})\ngem 'sqlite3', '~> 2.9.6', **(sqlite_adapter ? {} : {group: :test, require: false})\ngem 'with_advisory_lock', **(advisory_adapter ? {} : {group: :test, require: false})\n"
CANDIDATE_REPLACEMENTS = (
    (b"database_file = File.join(File.dirname(__FILE__), \"config/database.yml\")\n", b"mysql_adapter = false\nsqlite_adapter = false\nadvisory_adapter = false\ndatabase_file = File.join(File.dirname(__FILE__), \"config/database.yml\")\n"),
    (b"      when /mysql2/\n        gem 'mysql2', '~> 0.5.0'\n        gem \"with_advisory_lock\"\n", b"      when /mysql2/\n        mysql_adapter = true\n        advisory_adapter = true\n"),
    (b"      when /trilogy/\n        gem 'trilogy', '~> 2.9.0'\n        gem \"with_advisory_lock\"\n", b"      when /trilogy/\n        gem 'trilogy', '~> 2.9.0'\n        advisory_adapter = true\n"),
    (b"      when /sqlite3/\n        gem 'sqlite3', '~> 2.9.6'\n", b"      when /sqlite3/\n        sqlite_adapter = true\n"),
    (b"\n\ngroup :development, :test do\n", b"\n\n# Declare each driver once, loading only configured adapters by default.\ngem 'mysql2', '~> 0.5.0', **(mysql_adapter ? {} : {group: :test, require: false})\ngem 'sqlite3', '~> 2.9.6', **(sqlite_adapter ? {} : {group: :test, require: false})\ngem 'with_advisory_lock', **(advisory_adapter ? {} : {group: :test, require: false})\n\ngroup :development, :test do\n"),
)

_HEADERS = (b"GEM", b"PLATFORMS", b"DEPENDENCIES", b"RUBY VERSION", b"BUNDLED WITH")
# Critérios de revisão dos gemspecs oficiais; nunca usados para gerar o lock.
_NEW_SPECS = {
    b"mysql2": b"    mysql2 (0.5.7)\n      bigdecimal\n",
    b"with_advisory_lock": (
        b"    with_advisory_lock (7.6.0)\n"
        b"      activerecord (>= 7.2)\n"
    ),
}
_NEW_DEPENDENCIES = (b"  mysql2 (~> 0.5.0)\n", b"  with_advisory_lock\n")


def candidate_gemfile(raw: bytes) -> bytes:
    observed = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if observed != SOURCE_GEMFILE_BLOB:
        raise ValueError("DB_GEMFILE_SOURCE_CHANGED")
    for old, new in CANDIDATE_REPLACEMENTS:
        if raw.count(old) != 1:
            raise ValueError("DB_GEMFILE_DECLARATION_AMBIGUOUS")
        raw = raw.replace(old, new, 1)
    return raw


def _sections(raw: bytes) -> dict[bytes, bytes]:
    if (not isinstance(raw, bytes) or not raw or len(raw) > 100_000
            or not raw.isascii() or b"\r" in raw or b"\0" in raw
            or not raw.endswith(b"\n")):
        raise ValueError("DB_LOCK_INVALID_BYTES")
    matches = list(re.finditer(rb"(?m)^([A-Z][A-Z ]*)\n", raw))
    if (not matches or matches[0].start() != 0
            or tuple(match.group(1) for match in matches) != _HEADERS):
        raise ValueError("DB_LOCK_SECTIONS_CHANGED")
    return {
        match.group(1): raw[
            match.end():
            matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        ]
        for index, match in enumerate(matches)
    }


def _spec_pattern(name: bytes) -> re.Pattern[bytes]:
    return re.compile(
        rb"(?m)^    " + re.escape(name)
        + rb" \([^\n]+\)\n(?:      [^\n]+\n)*"
    )


def _remove_reviewed_additions(raw: bytes) -> bytes:
    sections = _sections(raw)
    marker = b"  specs:\n"
    if sections[b"GEM"].count(marker) != 1:
        raise ValueError("DB_LOCK_SPECS_MARKER_INVALID")
    prefix, specs = sections[b"GEM"].split(marker, 1)
    if prefix != b"  remote: https://rubygems.org/\n":
        raise ValueError("DB_LOCK_SOURCE_CHANGED")
    for name, expected_block in _NEW_SPECS.items():
        matches = list(_spec_pattern(name).finditer(specs))
        if len(matches) != 1 or matches[0].group(0) != expected_block:
            raise ValueError("DB_LOCK_NEW_SPEC_NOT_REVIEWED")
        match = matches[0]
        specs = specs[:match.start()] + specs[match.end():]
    for name in (b"bigdecimal", b"activerecord"):
        if not _spec_pattern(name).search(specs):
            raise ValueError("DB_LOCK_EXISTING_TRANSITIVE_MISSING")
    sections[b"GEM"] = prefix + marker + specs
    dependency_lines = sections[b"DEPENDENCIES"].splitlines(keepends=True)
    for line in _NEW_DEPENDENCIES:
        if dependency_lines.count(line) != 1:
            raise ValueError("DB_LOCK_NEW_DEPENDENCY_INVALID")
        dependency_lines.remove(line)
    sections[b"DEPENDENCIES"] = b"".join(dependency_lines)
    return b"".join(header + b"\n" + sections[header] for header in _HEADERS)


def require_database_only_additions(original: bytes, updated: bytes) -> None:
    before = _sections(original)
    for name in _NEW_SPECS:
        if _spec_pattern(name).search(before[b"GEM"]):
            raise ValueError("DB_LOCK_BASE_ALREADY_CONTAINS_ADDITION")
    if _remove_reviewed_additions(updated) != original:
        raise ValueError("DB_LOCK_CHANGED_EXISTING_BYTES")


def require_database_contract(lock: bytes) -> None:
    _remove_reviewed_additions(lock)


BUNDLER_DSL_PROBE = r"""
require 'rubygems'
gem 'bundler', '2.6.7'
require 'bundler'
require 'json'
require 'tmpdir'
require 'fileutils'
require 'digest'

raise 'DB_PROBE_BUNDLER_VERSION' unless Bundler::VERSION == '2.6.7'
source = File.realpath(Dir.pwd)
files = %w[Gemfile Gemfile.local Gemfile.lock config/database.yml]
snapshot = lambda do
  files.to_h do |name|
    path = File.join(source, name)
    [name, File.file?(path) ? Digest::SHA256.file(path).hexdigest : nil]
  end
end
before = snapshot.call
raw = File.binread(File.join(source, 'Gemfile'))
plugin_gemfiles = Dir.glob(File.join(source, 'plugins/*/{Gemfile,PluginGemfile}'))
raise 'DB_PROBE_PLUGIN_COPY_REVIEW_REQUIRED' unless plugin_gemfiles.empty?

locked = Bundler::LockfileParser.new(
  File.binread(File.join(source, 'Gemfile.lock'))
).dependencies
expected = locked.transform_values { |dependency| dependency.requirement.to_s }
{
  'mysql2' => '~> 0.5.0',
  'with_advisory_lock' => '>= 0'
}.each do |name, requirement|
  if expected.key?(name) && expected.fetch(name) != requirement
    raise 'DB_PROBE_LOCK_REQUIREMENT_CHANGED'
  end
  expected[name] = requirement
end

def evaluate_database_case(source, raw, adapter, expected)
  Dir.mktmpdir('db-bundle-contract-', ENV.fetch('RUNNER_TEMP')) do |temporary|
    File.binwrite(File.join(temporary, 'Gemfile'), raw)
    local = File.join(source, 'Gemfile.local')
    FileUtils.cp(local, temporary) if File.file?(local)
    FileUtils.mkdir_p(File.join(temporary, 'config'))
    if adapter
      File.write(
        File.join(temporary, 'config/database.yml'),
        "test:\n  adapter: #{adapter}\n  database: redmine_contract_disposable\n"
      )
    end
    dsl = Bundler::Dsl.new
    Dir.chdir(temporary) { dsl.eval_gemfile(File.join(temporary, 'Gemfile')) }
    dependencies = dsl.dependencies
    names = dependencies.map(&:name)
    raise 'DB_PROBE_DUPLICATE_DEPENDENCY' unless names.uniq.length == names.length
    observed = dependencies.to_h do |dependency|
      [dependency.name, dependency.requirement.to_s]
    end
    raise 'DB_PROBE_DEPENDENCIES_CHANGED' unless observed == expected

    %w[sqlite3 mysql2 with_advisory_lock pg].each do |name|
      dependency = dependencies.find { |item| item.name == name }
      raise 'DB_PROBE_ADAPTER_GEM_MISSING' unless dependency
      selected = (
        name == 'pg' ||
        (adapter == 'sqlite3' && name == 'sqlite3') ||
        (adapter == 'mysql2' && %w[mysql2 with_advisory_lock].include?(name))
      )
      expected_groups = selected ? [:default] : [:test]
      unless dependency.groups.sort == expected_groups
        raise 'DB_PROBE_ADAPTER_GROUP_CHANGED'
      end
      expected_require = selected ? nil : []
      unless dependency.autorequire == expected_require
        raise 'DB_PROBE_ADAPTER_REQUIRE_CHANGED'
      end
    end
    dependencies.map do |dependency|
      [
        dependency.name, dependency.requirement.to_s,
        dependency.platforms.map(&:to_s).sort
      ]
    end.sort
  end
end

cases = ['sqlite3', 'postgresql', 'mysql2', nil]
positive = lambda do
  results = cases.map { |adapter| evaluate_database_case(source, raw, adapter, expected) }
  raise 'DB_PROBE_MATRIX_DRIFT' unless results.uniq.length == 1
  results.first
end
signature = positive.call
begin
  evaluate_database_case(
    source, raw + "\ngem 'redmine_database_contract_negative_control'\n", nil, expected
  )
  raise 'DB_PROBE_NEGATIVE_DID_NOT_FAIL'
rescue RuntimeError => error
  raise unless error.message == 'DB_PROBE_DEPENDENCIES_CHANGED'
end
needle = "gem 'mysql2', '~> 0.5.0', **(mysql_adapter ? {} : {group: :test, require: false})"
unless raw.scan(Regexp.new(Regexp.escape(needle))).length == 1
  raise 'DB_PROBE_REQUIRE_CONTROL_AMBIGUOUS'
end
begin
  evaluate_database_case(
    source, raw.sub(needle, needle.sub('require: false', 'require: true')), nil, expected
  )
  raise 'DB_PROBE_REQUIRE_CONTROL_DID_NOT_FAIL'
rescue RuntimeError => error
  raise unless error.message == 'DB_PROBE_ADAPTER_REQUIRE_CHANGED'
end
raise 'DB_PROBE_REPLAY_CHANGED' unless positive.call == signature
raise 'DB_PROBE_SOURCE_CHANGED' unless snapshot.call == before
puts JSON.generate(
  status: 'passed', bundler: Bundler::VERSION, ruby: RUBY_VERSION,
  cases: ['sqlite3', 'postgresql', 'mysql2', 'absent'],
  dependency_count: signature.length,
  dependency_signature_sha256: Digest::SHA256.hexdigest(JSON.generate(signature)),
  negative_dependency_control: 'passed', negative_require_control: 'passed',
  replay: 'passed', source_preserved: true
)
"""
