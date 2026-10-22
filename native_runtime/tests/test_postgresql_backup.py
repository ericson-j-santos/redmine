import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "native_runtime.py"
spec = importlib.util.spec_from_file_location("native_runtime", MODULE_PATH)
native = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(native)

SHA = "a" * 40
WRONG_SHA = "b" * 40
DATABASE_URL = "postgresql://redmine:unit-test-password@127.0.0.1:5432/redmine_source"
RESTORE_DATABASE_URL = "postgresql://redmine:restore-password@127.0.0.1:5432/redmine_restore"


def make_target(root: Path, *, symlink: bool = False) -> Path:
    target = root / "target"
    release = target / "releases" / SHA
    release.mkdir(parents=True)
    (target / "current").symlink_to(Path("releases") / SHA, target_is_directory=True)
    for name in ("db", "files", "config", "tmp", "log", "backups"):
        (target / "shared" / name).mkdir(parents=True, exist_ok=True)
    (target / "shared/files/attachment.txt").write_text("attachment\n", encoding="utf-8")
    (target / "shared/config/secret_token.rb").write_text("test-secret-config\n", encoding="utf-8")
    if symlink:
        outside = root / "outside.txt"
        outside.write_text("must-not-be-followed\n", encoding="utf-8")
        (target / "shared/files/outside-link").symlink_to(outside)
    return target


class FakePostgresTools:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []
        self.environments: list[dict[str, str]] = []
        self.restored = False
        self.force_schema_entry = False
        self.privileged_role = False
        self.unsafe_role_memberships = False

    @staticmethod
    def _output_path(command: list[str]) -> Path:
        for index, value in enumerate(command):
            if value == "--file" and index + 1 < len(command):
                return Path(command[index + 1])
            if value.startswith("--file="):
                return Path(value.split("=", 1)[1])
            if value == "-f" and index + 1 < len(command):
                return Path(command[index + 1])
        raise AssertionError(f"pg_dump output was not explicit: {command!r}")

    def __call__(self, command, *args, **kwargs):
        command = [str(value) for value in command]
        self.commands.append(command)
        self.environments.append(dict(kwargs.get("env", {})))
        executable = Path(command[0]).name
        if "--version" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=f"{executable} (PostgreSQL) 16.4\n",
                stderr="",
            )
        if executable == "pg_dump":
            output = self._output_path(command)
            output.parent.mkdir(parents=True, exist_ok=True)
            if "--schema-only" in command:
                marker = (
                    b"PGDMP_NONEMPTY"
                    if self.restored or self.force_schema_entry
                    else b"PGDMP_EMPTY"
                )
                output.write_bytes(marker + b"\x01\x0f\x00unit-test-schema-archive")
            else:
                output.write_bytes(b"PGDMP\x01\x0f\x00unit-test-archive")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if executable == "psql" and "pg_encoding_to_char" in command[-1]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=(
                    '{"encoding":"UTF8","lc_collate":"C.UTF-8",'
                    '"lc_ctype":"C.UTF-8","locale_provider":"c",'
                    '"icu_locale":"","icu_rules":"","collation_version":""}\n'
                ),
                stderr="",
            )
        if executable == "psql" and "pg_largeobject_metadata" in command[-1]:
            return subprocess.CompletedProcess(command, 0, stdout="0\n", stderr="")
        if executable == "psql" and "role.rolsuper" in command[-1]:
            superuser = "true" if self.privileged_role else "false"
            memberships = 1 if self.unsafe_role_memberships else 0
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=(
                    f'{{"superuser":{superuser},"create_role":false,"create_database":false,'
                    '"replication":false,"bypass_rls":false,"login":true,'
                    f'"owns_database":true,"effective_memberships":{memberships}}}\n'
                ),
                stderr="",
            )
        if executable == "pg_restore" and any(value in ("--list", "-l") for value in command[1:]):
            archive = Path(command[-1])
            if archive.read_bytes().startswith(b"PGDMP_EMPTY"):
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout=";\n; Selected TOC Entries:\n;\n",
                    stderr="",
                )
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="1; 0 0 TABLE public projects redmine\n",
                stderr="",
            )
        if executable == "pg_restore":
            self.restored = True
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    def mutating_restore_commands(self) -> list[list[str]]:
        return [
            command
            for command in self.commands
            if Path(command[0]).name == "pg_restore"
            and "--version" not in command
            and not any(value in ("--list", "-l") for value in command[1:])
        ]


def installed_metadata() -> dict:
    return {
        "schema_version": native.SCHEMA_VERSION,
        "repository": native.REPOSITORY,
        "source_sha": SHA,
        "source_release_manifest_sha256": "c" * 64,
        "application_tree_sha256": "d" * 64,
    }


def postgres_snapshot() -> dict[str, int | str]:
    return {
        "schema_migrations_count": 1,
        "schema_migrations_max": "20261022000000",
        "projects_count": 1,
        "projects_max_id": 1,
        "issues_count": 1,
        "issues_max_id": 1,
        "attachments_count": 1,
        "attachments_max_id": 1,
        "users_count": 1,
        "users_max_id": 1,
    }


def postgres_database_settings() -> dict[str, str]:
    return {
        "encoding": "UTF8",
        "lc_collate": "C.UTF-8",
        "lc_ctype": "C.UTF-8",
        "locale_provider": "c",
        "icu_locale": "",
        "icu_rules": "",
        "collation_version": "",
    }


def postgres_role_profile() -> dict[str, bool | int]:
    return {
        "superuser": False,
        "create_role": False,
        "create_database": False,
        "replication": False,
        "bypass_rls": False,
        "login": True,
        "owns_database": True,
        "effective_memberships": 0,
    }


class PostgreSQLBackupTests(unittest.TestCase):
    def test_postgres_connection_uses_minimal_environment_and_rejects_semantic_options(self):
        inherited = {
            "PATH": "/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "DATABASE_URL": "postgresql://leaked-source",
            "REQSYS_RESTORE_DATABASE_URL": "postgresql://leaked-restore",
            "REQSYS_REPLAY_DATABASE_URL": "postgresql://leaked-replay",
            "PGOPTIONS": "-c search_path=attacker",
            "UNRELATED_SECRET": "must-not-reach-postgres-tools",
        }
        with mock.patch.dict(native.os.environ, inherited, clear=True):
            env, identity = native._postgres_connection(
                DATABASE_URL + "?sslmode=require&connect_timeout=30"
            )

        self.assertEqual(
            env,
            {
                "PATH": "/usr/bin:/bin",
                "LANG": "C.UTF-8",
                "PGHOST": "127.0.0.1",
                "PGPORT": "5432",
                "PGDATABASE": "redmine_source",
                "PGAPPNAME": "reqsys-native-backup",
                "PGCONNECT_TIMEOUT": "30",
                "PGPASSFILE": native.os.devnull,
                "PGUSER": "redmine",
                "PGPASSWORD": "unit-test-password",
                "PGSSLMODE": "require",
            },
        )
        self.assertRegex(identity, r"^[0-9a-f]{64}$")

        for query in (
            "options=-c%20search_path%3Dattacker",
            "application_name=caller-controlled",
            "sslmode=invalid",
            "connect_timeout=0",
        ):
            with self.subTest(query=query), self.assertRaises(native.NativeRuntimeError):
                native._postgres_connection(DATABASE_URL + "?" + query)
        with self.assertRaises(native.NativeRuntimeError):
            native._postgres_connection(
                "postgresql://redmine:password%0Ainjected@127.0.0.1:5432/redmine_source"
            )

        tools = FakePostgresTools()
        with mock.patch.dict(native.os.environ, inherited, clear=True), mock.patch.object(
            native.subprocess, "run", side_effect=tools
        ):
            self.assertEqual(native._postgres_tool_version("pg_dump")["major"], 16)
        self.assertEqual(tools.environments, [{"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}])

        with mock.patch.object(native, "_postgres_query", return_value="150012"):
            with self.assertRaisesRegex(
                native.NativeRuntimeError,
                "NATIVE_POSTGRES_SERVER_VERSION_UNSUPPORTED",
            ):
                native._postgres_server_version(DATABASE_URL)

    def test_backup_requires_quiesce_before_postgres_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = make_target(root)
            output = root / "backup"
            with mock.patch.object(native, "verify_install", return_value=installed_metadata()), mock.patch.object(
                native.subprocess, "run"
            ) as run:
                with self.assertRaises(native.NativeRuntimeError):
                    native.backup_postgresql(
                        target,
                        output,
                        SHA,
                        DATABASE_URL,
                        quiesced=False,
                    )
            run.assert_not_called()
            self.assertFalse(output.exists())

    def test_backup_rejects_privileged_database_role(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = make_target(root)
            output = root / "backup"
            tools = FakePostgresTools()
            tools.privileged_role = True
            with mock.patch.object(native, "verify_install", return_value=installed_metadata()), mock.patch.object(
                native, "_postgres_server_version", return_value={"version_num": 160004, "major": 16}
            ), mock.patch.object(native.subprocess, "run", side_effect=tools):
                with self.assertRaisesRegex(
                    native.NativeRuntimeError, "NATIVE_POSTGRES_ROLE_PROFILE_INVALID"
                ):
                    native.backup_postgresql(
                        target,
                        output,
                        SHA,
                        DATABASE_URL,
                        quiesced=True,
                    )
            self.assertFalse(output.exists())
            self.assertFalse(
                any(
                    Path(command[0]).name == "pg_dump" and "--version" not in command
                    for command in tools.commands
                )
            )

    def test_backup_rejects_database_role_memberships(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = make_target(root)
            output = root / "backup"
            tools = FakePostgresTools()
            tools.unsafe_role_memberships = True
            with mock.patch.object(native, "verify_install", return_value=installed_metadata()), mock.patch.object(
                native, "_postgres_server_version", return_value={"version_num": 160004, "major": 16}
            ), mock.patch.object(native.subprocess, "run", side_effect=tools):
                with self.assertRaisesRegex(
                    native.NativeRuntimeError, "NATIVE_POSTGRES_ROLE_PROFILE_INVALID"
                ):
                    native.backup_postgresql(
                        target,
                        output,
                        SHA,
                        DATABASE_URL,
                        quiesced=True,
                    )
            self.assertFalse(output.exists())
            self.assertFalse(
                any(
                    Path(command[0]).name == "pg_dump" and "--version" not in command
                    for command in tools.commands
                )
            )

    def test_backup_rejects_special_node_without_running_dump(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = make_target(root)
            native.os.mkfifo(target / "shared/files/blocked-fifo")
            output = root / "backup"
            tools = FakePostgresTools()
            with mock.patch.object(native, "verify_install", return_value=installed_metadata()), mock.patch.object(
                native, "_postgres_readback", return_value=postgres_snapshot()
            ), mock.patch.object(
                native, "_postgres_server_version", return_value={"version_num": 160004, "major": 16}
            ), mock.patch.object(native.subprocess, "run", side_effect=tools):
                with self.assertRaisesRegex(native.NativeRuntimeError, "NATIVE_STATE_NODE_INVALID"):
                    native.backup_postgresql(
                        target,
                        output,
                        SHA,
                        DATABASE_URL,
                        quiesced=True,
                    )
            self.assertFalse(output.exists())
            self.assertFalse(
                any(
                    Path(command[0]).name == "pg_dump" and "--version" not in command
                    for command in tools.commands
                )
            )

    def test_backup_requires_attachment_and_configuration_components(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for component in ("files", "config"):
                with self.subTest(component=component):
                    case_root = root / component
                    case_root.mkdir()
                    target = make_target(case_root)
                    native.shutil.rmtree(target / "shared" / component)
                    output = case_root / "backup"
                    tools = FakePostgresTools()
                    with mock.patch.object(
                        native, "verify_install", return_value=installed_metadata()
                    ), mock.patch.object(
                        native, "_postgres_readback", return_value=postgres_snapshot()
                    ), mock.patch.object(
                        native,
                        "_postgres_server_version",
                        return_value={"version_num": 160004, "major": 16},
                    ), mock.patch.object(native.subprocess, "run", side_effect=tools):
                        with self.assertRaisesRegex(
                            native.NativeRuntimeError, "NATIVE_STATE_COMPONENT_MISSING"
                        ):
                            native.backup_postgresql(
                                target,
                                output,
                                SHA,
                                DATABASE_URL,
                                quiesced=True,
                            )
                    self.assertFalse(output.exists())
                    self.assertFalse(
                        any(
                            Path(command[0]).name == "pg_dump" and "--version" not in command
                            for command in tools.commands
                        )
                    )

    def test_backup_copy_detects_regular_file_swapped_to_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = make_target(root)
            source_file = target / "shared/files/attachment.txt"
            outside = root / "outside-secret.txt"
            outside.write_text("outside-must-not-be-copied\n", encoding="utf-8")
            output = root / "backup"
            tools = FakePostgresTools()
            original_entry_stat = native._entry_stat
            swapped = False

            def swap_after_lstat(directory, name, error_code):
                nonlocal swapped
                result = original_entry_stat(directory, name, error_code)
                if name == "attachment.txt" and not swapped:
                    source_file.unlink()
                    source_file.symlink_to(outside)
                    swapped = True
                return result

            with mock.patch.object(native, "verify_install", return_value=installed_metadata()), mock.patch.object(
                native, "_postgres_readback", return_value=postgres_snapshot()
            ), mock.patch.object(
                native, "_postgres_server_version", return_value={"version_num": 160004, "major": 16}
            ), mock.patch.object(
                native, "_entry_stat", side_effect=swap_after_lstat
            ), mock.patch.object(native.subprocess, "run", side_effect=tools):
                with self.assertRaises(native.NativeRuntimeError):
                    native.backup_postgresql(
                        target,
                        output,
                        SHA,
                        DATABASE_URL,
                        quiesced=True,
                    )
            self.assertTrue(swapped)
            self.assertFalse(output.exists())
            self.assertEqual(outside.read_text(encoding="utf-8"), "outside-must-not-be-copied\n")
            self.assertFalse(
                any(
                    Path(command[0]).name == "pg_dump" and "--version" not in command
                    for command in tools.commands
                )
            )

    def test_backup_rejects_output_nested_in_copied_components(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = make_target(root)
            with mock.patch.object(native, "verify_install", return_value=installed_metadata()), mock.patch.object(
                native.subprocess, "run"
            ) as run:
                for component in ("files", "config"):
                    with self.subTest(component=component):
                        parent = target / "shared" / component / "nested"
                        parent.mkdir()
                        output = parent / "backup"
                        with self.assertRaisesRegex(
                            native.NativeRuntimeError, "NATIVE_BACKUP_OUTPUT_RECURSIVE"
                        ):
                            native.backup_postgresql(
                                target,
                                output,
                                SHA,
                                DATABASE_URL,
                                quiesced=True,
                            )
                        self.assertFalse(output.exists())
            run.assert_not_called()

    def test_backup_manifest_hashes_all_state_and_detects_each_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = make_target(root)
            output = root / "backup"
            tools = FakePostgresTools()
            snapshot = postgres_snapshot()
            with mock.patch.object(native, "verify_install", return_value=installed_metadata()), mock.patch.object(
                native, "_postgres_readback", return_value=snapshot
            ), mock.patch.object(
                native, "_postgres_server_version", return_value={"version_num": 160004, "major": 16}
            ), mock.patch.object(native.subprocess, "run", side_effect=tools):
                manifest = native.backup_postgresql(
                    target,
                    output,
                    SHA,
                    DATABASE_URL,
                    quiesced=True,
                )
                self.assertEqual(native.verify_backup(output, SHA), manifest)

                self.assertEqual(manifest["database_adapter"], "postgresql")
                self.assertEqual(
                    manifest["database"]["database_settings"],
                    postgres_database_settings(),
                )
                self.assertEqual(
                    manifest["database"]["role_profile"],
                    postgres_role_profile(),
                )
                self.assertEqual(manifest["source_identity"]["source_sha"], SHA)
                self.assertTrue(manifest["quiesced"])
                self.assertTrue(manifest["contains_secrets"])
                hashes = manifest["files_sha256"]
                self.assertIn("db/redmine.pgdump", hashes)
                self.assertIn("files/attachment.txt", hashes)
                self.assertIn("config/secret_token.rb", hashes)
                self.assertEqual(hashes, native._backup_hashes(output))

                for relative in (
                    "db/redmine.pgdump",
                    "files/attachment.txt",
                    "config/secret_token.rb",
                ):
                    with self.subTest(relative=relative):
                        path = output / relative
                        original = path.read_bytes()
                        path.write_bytes(original + b"tamper")
                        with self.assertRaises(native.NativeRuntimeError):
                            native.verify_backup(output, SHA)
                        path.write_bytes(original)
                        self.assertEqual(native.verify_backup(output, SHA), manifest)

                with self.assertRaises(native.NativeRuntimeError):
                    native.verify_backup(output, WRONG_SHA)

            flattened = "\n".join(" ".join(command) for command in tools.commands)
            self.assertNotIn("unit-test-password", flattened)
            self.assertNotIn(DATABASE_URL, flattened)
            dump_commands = [
                command
                for command in tools.commands
                if Path(command[0]).name == "pg_dump" and "--version" not in command
            ]
            self.assertEqual(len(dump_commands), 1)
            self.assertIn("--no-password", dump_commands[0])
            self.assertIn("--no-tablespaces", dump_commands[0])

    def test_wrong_sha_is_rejected_before_restore_mutates_database_or_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = make_target(root)
            backup = root / "backup"
            tools = FakePostgresTools()
            snapshot = postgres_snapshot()
            with mock.patch.object(native, "verify_install", return_value=installed_metadata()), mock.patch.object(
                native, "_postgres_readback", return_value=snapshot
            ), mock.patch.object(
                native, "_postgres_server_version", return_value={"version_num": 160004, "major": 16}
            ), mock.patch.object(native.subprocess, "run", side_effect=tools):
                native.backup_postgresql(target, backup, SHA, DATABASE_URL, quiesced=True)

                state = root / "wrong-sha-state"
                before_commands = len(tools.mutating_restore_commands())
                with self.assertRaises(native.NativeRuntimeError):
                    native.restore_postgresql(
                        backup,
                        state,
                        WRONG_SHA,
                        RESTORE_DATABASE_URL,
                    )
                self.assertFalse(state.exists())
                self.assertEqual(len(tools.mutating_restore_commands()), before_commands)

    def test_restore_rechecks_staged_hashes_before_database_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = make_target(root)
            backup = root / "backup"
            tools = FakePostgresTools()
            snapshot = postgres_snapshot()
            with mock.patch.object(native, "verify_install", return_value=installed_metadata()), mock.patch.object(
                native, "_postgres_readback", return_value=snapshot
            ), mock.patch.object(
                native, "_postgres_user_object_count", return_value=0
            ), mock.patch.object(
                native, "_postgres_server_version", return_value={"version_num": 160004, "major": 16}
            ), mock.patch.object(native.subprocess, "run", side_effect=tools):
                native.backup_postgresql(target, backup, SHA, DATABASE_URL, quiesced=True)
                original_copy = native._copy_backup_component
                changed = False

                def alter_after_initial_verify(source: Path, destination: Path) -> None:
                    nonlocal changed
                    if source == backup / "files" and not changed:
                        with (source / "attachment.txt").open("ab") as stream:
                            stream.write(b"changed-after-verify")
                        changed = True
                    original_copy(source, destination)

                restored = root / "restored-after-race"
                restore_count = len(tools.mutating_restore_commands())
                with mock.patch.object(
                    native, "_copy_backup_component", side_effect=alter_after_initial_verify
                ), self.assertRaisesRegex(
                    native.NativeRuntimeError, "NATIVE_POSTGRES_RESTORE_STAGING_HASH_MISMATCH"
                ):
                    native.restore_postgresql(
                        backup,
                        restored,
                        SHA,
                        RESTORE_DATABASE_URL,
                    )
                self.assertTrue(changed)
                self.assertFalse(restored.exists())
                self.assertEqual(len(tools.mutating_restore_commands()), restore_count)

    def test_restore_rejects_manifest_change_immediately_before_database_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = make_target(root)
            backup = root / "backup"
            tools = FakePostgresTools()
            snapshot = postgres_snapshot()
            with mock.patch.object(native, "verify_install", return_value=installed_metadata()), mock.patch.object(
                native, "_postgres_readback", return_value=snapshot
            ), mock.patch.object(
                native, "_postgres_server_version", return_value={"version_num": 160004, "major": 16}
            ), mock.patch.object(native.subprocess, "run", side_effect=tools):
                native.backup_postgresql(target, backup, SHA, DATABASE_URL, quiesced=True)
                original_pristine_check = native._require_postgres_pristine_target
                checks = 0

                def alter_manifest_after_final_pristine_check(
                    database_url: str,
                    working_directory: Path,
                ) -> None:
                    nonlocal checks
                    original_pristine_check(database_url, working_directory)
                    checks += 1
                    if checks == 2:
                        with (backup / "manifest.json").open("ab") as stream:
                            stream.write(b" ")

                restored = root / "restored-after-manifest-race"
                restore_count = len(tools.mutating_restore_commands())
                with mock.patch.object(
                    native,
                    "_require_postgres_pristine_target",
                    side_effect=alter_manifest_after_final_pristine_check,
                ), self.assertRaisesRegex(
                    native.NativeRuntimeError, "NATIVE_BACKUP_MANIFEST_CHANGED"
                ):
                    native.restore_postgresql(
                        backup,
                        restored,
                        SHA,
                        RESTORE_DATABASE_URL,
                    )
                self.assertEqual(checks, 2)
                self.assertFalse(restored.exists())
                self.assertEqual(len(tools.mutating_restore_commands()), restore_count)

    def test_restore_rechecks_staging_after_final_pristine_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = make_target(root)
            backup = root / "backup"
            tools = FakePostgresTools()
            snapshot = postgres_snapshot()
            with mock.patch.object(native, "verify_install", return_value=installed_metadata()), mock.patch.object(
                native, "_postgres_readback", return_value=snapshot
            ), mock.patch.object(
                native, "_postgres_server_version", return_value={"version_num": 160004, "major": 16}
            ), mock.patch.object(native.subprocess, "run", side_effect=tools):
                native.backup_postgresql(target, backup, SHA, DATABASE_URL, quiesced=True)
                original_pristine_check = native._require_postgres_pristine_target
                restored = root / "restored-after-preflight-race"
                staging = root / f".{restored.name}.staging-{native.os.getpid()}"
                checks = 0

                def alter_archive_after_final_pristine_check(
                    database_url: str,
                    working_directory: Path,
                ) -> None:
                    nonlocal checks
                    original_pristine_check(database_url, working_directory)
                    checks += 1
                    if checks == 2:
                        with (staging / native.POSTGRES_ARCHIVE).open("ab") as stream:
                            stream.write(b"changed-during-final-preflight")

                restore_count = len(tools.mutating_restore_commands())
                with mock.patch.object(
                    native,
                    "_require_postgres_pristine_target",
                    side_effect=alter_archive_after_final_pristine_check,
                ), self.assertRaisesRegex(
                    native.NativeRuntimeError,
                    "NATIVE_POSTGRES_RESTORE_STAGING_HASH_MISMATCH",
                ):
                    native.restore_postgresql(
                        backup,
                        restored,
                        SHA,
                        RESTORE_DATABASE_URL,
                    )
                self.assertEqual(checks, 2)
                self.assertFalse(restored.exists())
                self.assertEqual(len(tools.mutating_restore_commands()), restore_count)

    def test_restore_rechecks_database_empty_immediately_before_pg_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = make_target(root)
            backup = root / "backup"
            tools = FakePostgresTools()
            snapshot = postgres_snapshot()
            with mock.patch.object(native, "verify_install", return_value=installed_metadata()), mock.patch.object(
                native, "_postgres_readback", return_value=snapshot
            ), mock.patch.object(
                native, "_postgres_server_version", return_value={"version_num": 160004, "major": 16}
            ), mock.patch.object(native.subprocess, "run", side_effect=tools):
                native.backup_postgresql(target, backup, SHA, DATABASE_URL, quiesced=True)
                checks = iter((0, 1))
                restored = root / "target-became-nonempty"
                restore_count = len(tools.mutating_restore_commands())
                with mock.patch.object(
                    native, "_postgres_nondumpable_count", side_effect=lambda _url: next(checks)
                ), self.assertRaisesRegex(
                    native.NativeRuntimeError, "NATIVE_POSTGRES_RESTORE_TARGET_NOT_EMPTY"
                ):
                    native.restore_postgresql(
                        backup,
                        restored,
                        SHA,
                        RESTORE_DATABASE_URL,
                    )
                self.assertFalse(restored.exists())
                self.assertEqual(len(tools.mutating_restore_commands()), restore_count)

    def test_restore_rejects_nonempty_schema_toc_before_database_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = make_target(root)
            backup = root / "backup"
            tools = FakePostgresTools()
            snapshot = postgres_snapshot()
            with mock.patch.object(native, "verify_install", return_value=installed_metadata()), mock.patch.object(
                native, "_postgres_readback", return_value=snapshot
            ), mock.patch.object(
                native, "_postgres_server_version", return_value={"version_num": 160004, "major": 16}
            ), mock.patch.object(native.subprocess, "run", side_effect=tools):
                native.backup_postgresql(target, backup, SHA, DATABASE_URL, quiesced=True)
                tools.force_schema_entry = True
                restored = root / "nonempty-schema-target"
                restore_count = len(tools.mutating_restore_commands())
                with self.assertRaisesRegex(
                    native.NativeRuntimeError, "NATIVE_POSTGRES_RESTORE_TARGET_NOT_EMPTY"
                ):
                    native.restore_postgresql(
                        backup,
                        restored,
                        SHA,
                        RESTORE_DATABASE_URL,
                    )
                self.assertFalse(restored.exists())
                self.assertEqual(len(tools.mutating_restore_commands()), restore_count)

    def test_restore_rejects_database_encoding_or_locale_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = make_target(root)
            backup = root / "backup"
            tools = FakePostgresTools()
            snapshot = postgres_snapshot()
            with mock.patch.object(native, "verify_install", return_value=installed_metadata()), mock.patch.object(
                native, "_postgres_readback", return_value=snapshot
            ), mock.patch.object(
                native, "_postgres_server_version", return_value={"version_num": 160004, "major": 16}
            ), mock.patch.object(native.subprocess, "run", side_effect=tools):
                native.backup_postgresql(target, backup, SHA, DATABASE_URL, quiesced=True)
                restored = root / "locale-mismatch"
                restore_count = len(tools.mutating_restore_commands())
                with mock.patch.object(
                    native,
                    "_postgres_database_settings",
                    return_value={**postgres_database_settings(), "lc_collate": "C", "lc_ctype": "C"},
                ), self.assertRaisesRegex(
                    native.NativeRuntimeError, "NATIVE_POSTGRES_DATABASE_SETTINGS_MISMATCH"
                ):
                    native.restore_postgresql(
                        backup,
                        restored,
                        SHA,
                        RESTORE_DATABASE_URL,
                    )
                self.assertFalse(restored.exists())
                self.assertEqual(len(tools.mutating_restore_commands()), restore_count)

    def test_restore_readback_and_replay_refusal_leave_first_restore_intact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = make_target(root)
            backup = root / "backup"
            tools = FakePostgresTools()
            snapshot = postgres_snapshot()

            def object_count(_url: str) -> int:
                return 3 if tools.restored else 0

            leaked_environment = {
                "DATABASE_URL": "postgresql://inherited-source-secret",
                "REQSYS_RESTORE_DATABASE_URL": "postgresql://inherited-restore-secret",
                "REQSYS_REPLAY_DATABASE_URL": "postgresql://inherited-replay-secret",
                "UNRELATED_SECRET": "arbitrary-inherited-secret",
            }
            with mock.patch.dict(native.os.environ, leaked_environment, clear=False), mock.patch.object(
                native, "verify_install", return_value=installed_metadata()
            ), mock.patch.object(
                native, "_postgres_readback", return_value=snapshot
            ) as readback, mock.patch.object(
                native, "_postgres_user_object_count", side_effect=object_count
            ), mock.patch.object(
                native, "_postgres_server_version", return_value={"version_num": 160004, "major": 16}
            ), mock.patch.object(native.subprocess, "run", side_effect=tools):
                manifest = native.backup_postgresql(target, backup, SHA, DATABASE_URL, quiesced=True)
                restored = root / "restored-state"
                self.assertEqual(
                    native.restore_postgresql(
                        backup,
                        restored,
                        SHA,
                        RESTORE_DATABASE_URL,
                    ),
                    manifest,
                )
                self.assertGreaterEqual(readback.call_count, 2)
                self.assertEqual((restored / "files/attachment.txt").read_text(), "attachment\n")
                self.assertEqual(
                    (restored / "config/secret_token.rb").read_text(),
                    "test-secret-config\n",
                )
                receipt = restored / native.POSTGRES_RESTORE_RECEIPT
                self.assertTrue(receipt.is_file())
                self.assertTrue((restored / "db").is_dir())
                self.assertFalse((restored / native.POSTGRES_ARCHIVE).exists())
                self.assertEqual(list((restored / "db").iterdir()), [])
                receipt_before = receipt.read_bytes()
                state_hash_before = hashlib.sha256(
                    (restored / "files/attachment.txt").read_bytes()
                    + (restored / "config/secret_token.rb").read_bytes()
                ).hexdigest()
                restore_count = len(tools.mutating_restore_commands())

                nonempty_state = root / "nonempty-database-state"
                with self.assertRaisesRegex(
                    native.NativeRuntimeError, "NATIVE_POSTGRES_RESTORE_TARGET_NOT_EMPTY"
                ):
                    native.restore_postgresql(
                        backup,
                        nonempty_state,
                        SHA,
                        RESTORE_DATABASE_URL,
                    )
                self.assertFalse(nonempty_state.exists())
                self.assertEqual(len(tools.mutating_restore_commands()), restore_count)

                inside_backup = backup / "restored-state"
                with self.assertRaisesRegex(
                    native.NativeRuntimeError, "NATIVE_RESTORE_TARGET_INSIDE_BACKUP"
                ):
                    native.restore_postgresql(
                        backup,
                        inside_backup,
                        SHA,
                        RESTORE_DATABASE_URL,
                    )
                self.assertFalse(inside_backup.exists())
                self.assertEqual(len(tools.mutating_restore_commands()), restore_count)

                with self.assertRaises(native.NativeRuntimeError):
                    native.restore_postgresql(
                        backup,
                        restored,
                        SHA,
                        RESTORE_DATABASE_URL,
                    )

                self.assertEqual(receipt.read_bytes(), receipt_before)
                self.assertEqual(len(tools.mutating_restore_commands()), restore_count)
                self.assertEqual(
                    hashlib.sha256(
                        (restored / "files/attachment.txt").read_bytes()
                        + (restored / "config/secret_token.rb").read_bytes()
                    ).hexdigest(),
                    state_hash_before,
                )
            for child_environment in tools.environments:
                self.assertNotIn("DATABASE_URL", child_environment)
                self.assertNotIn("REQSYS_RESTORE_DATABASE_URL", child_environment)
                self.assertNotIn("REQSYS_REPLAY_DATABASE_URL", child_environment)
                self.assertNotIn("UNRELATED_SECRET", child_environment)
                for leaked_value in leaked_environment.values():
                    self.assertNotIn(leaked_value, child_environment.values())
            for command in tools.commands:
                executable = Path(command[0]).name
                if executable == "psql":
                    self.assertIn("--no-password", command)
                elif executable == "pg_dump" and "--version" not in command:
                    self.assertIn("--no-password", command)
                    self.assertIn("--no-tablespaces", command)
                elif (
                    executable == "pg_restore"
                    and "--version" not in command
                    and "--list" not in command
                ):
                    self.assertIn("--no-password", command)
                    self.assertIn("--no-tablespaces", command)

    def test_backup_rejects_source_symlink_without_following_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = make_target(root, symlink=True)
            output = root / "backup"
            tools = FakePostgresTools()
            with mock.patch.object(native, "verify_install", return_value=installed_metadata()), mock.patch.object(
                native, "_postgres_readback", return_value={}
            ), mock.patch.object(
                native, "_postgres_server_version", return_value={"version_num": 160004, "major": 16}
            ), mock.patch.object(native.subprocess, "run", side_effect=tools):
                with self.assertRaises(native.NativeRuntimeError):
                    native.backup_postgresql(
                        target,
                        output,
                        SHA,
                        DATABASE_URL,
                        quiesced=True,
                    )
            self.assertFalse(output.exists())
            self.assertFalse(
                any(
                    Path(command[0]).name == "pg_dump" and "--version" not in command
                    for command in tools.commands
                )
            )


if __name__ == "__main__":
    unittest.main()
