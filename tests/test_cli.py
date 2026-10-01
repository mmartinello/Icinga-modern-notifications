"""Tests for the command-line interface."""

import contextlib
import io
import unittest
from pathlib import Path

from icinga_modern_notifications.cli import build_parser, notification_from_args
from icinga_modern_notifications.model import DisplayStatus, ObjectKind, State, Tag

from .helpers import HOST_ARGS, SERVICE_ARGS, run_cli


def parse(argv):
    """Parse ``argv`` and return (namespace, notification)."""
    args = build_parser().parse_args(argv)
    return args, notification_from_args(args)


def parse_error(argv) -> str:
    """Parse invalid ``argv`` and return the argparse error message."""
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        with unittest.TestCase().assertRaises(SystemExit) as ctx:
            build_parser().parse_args(argv)
    assert ctx.exception.code == 2
    return stderr.getvalue()


def without(argv, option):
    """Return ``argv`` without ``option`` and its value."""
    index = argv.index(option)
    return argv[:index] + argv[index + 2:]


class HelpTests(unittest.TestCase):
    def test_help_commands(self):
        for argv in (
            ["--help"],
            ["mail", "--help"],
            ["mail", "host", "--help"],
            ["mail", "service", "--help"],
        ):
            with self.subTest(argv=argv):
                code, out, _ = run_cli(*argv)
                self.assertEqual(code, 0)
                self.assertIn("usage:", out)

    def test_service_help_lists_service_options(self):
        _, out, _ = run_cli("mail", "service", "--help")
        self.assertIn("--service ", out)
        self.assertIn("--service-display-name", out)
        _, out, _ = run_cli("mail", "host", "--help")
        self.assertNotIn("--service", out)

    def test_missing_channel_is_usage_error(self):
        code, _, err = run_cli()
        self.assertEqual(code, 2)
        self.assertIn("usage:", err)

    def test_unknown_channel_is_usage_error(self):
        code, _, err = run_cli("pigeon", "host")
        self.assertEqual(code, 2)
        self.assertIn("invalid choice", err)

    def test_missing_kind_is_usage_error(self):
        code, _, _ = run_cli("mail")
        self.assertEqual(code, 2)


class HostParsingTests(unittest.TestCase):
    def test_minimal_host(self):
        args, n = parse(HOST_ARGS)
        self.assertEqual(args.channel, "mail")
        self.assertIs(n.kind, ObjectKind.HOST)
        self.assertEqual(n.notification_type, "PROBLEM")
        self.assertIs(n.state, State.DOWN)
        self.assertEqual(n.host, "postgres01")
        self.assertEqual(n.output, "PING CRITICAL - Packet loss = 100%")
        self.assertEqual(n.timestamp, 1790000000)
        self.assertIsNone(n.service)
        self.assertEqual(args.mail_from, "Icinga <icinga@example.com>")
        self.assertEqual(args.mail_to, ["admin@example.com"])

    def test_host_rejects_service_option(self):
        err = parse_error(HOST_ARGS + ["--service", "PostgreSQL"])
        self.assertIn("unrecognized arguments", err)

    def test_timestamp_defaults_to_now(self):
        _, n = parse(without(HOST_ARGS, "--timestamp"))
        self.assertGreater(n.timestamp, 1700000000)


class ServiceParsingTests(unittest.TestCase):
    def test_minimal_service(self):
        _, n = parse(SERVICE_ARGS)
        self.assertIs(n.kind, ObjectKind.SERVICE)
        self.assertIs(n.state, State.CRITICAL)
        self.assertEqual(n.service, "PostgreSQL")
        self.assertIs(n.display_status, DisplayStatus.CRITICAL)

    def test_service_is_required(self):
        err = parse_error(without(SERVICE_ARGS, "--service"))
        self.assertIn("--service", err)


class RequiredArgumentTests(unittest.TestCase):
    def test_required_options(self):
        for option in (
            "--notification-type",
            "--state",
            "--host",
            "--output",
            "--from",
            "--to",
        ):
            with self.subTest(option=option):
                err = parse_error(without(SERVICE_ARGS, option))
                self.assertIn("required", err)
                self.assertIn(option, err)


class RecipientTests(unittest.TestCase):
    def test_repeatable_to(self):
        args, _ = parse(SERVICE_ARGS + ["--to", "noc@example.com"])
        self.assertEqual(args.mail_to, ["admin@example.com", "noc@example.com"])
        settings = args.channel_impl.settings(args)
        self.assertEqual(settings.recipients, ("admin@example.com", "noc@example.com"))
        self.assertEqual(settings.sender, "Icinga <icinga@example.com>")

    def test_invalid_recipient(self):
        argv = SERVICE_ARGS + ["--to", "not-an-address"]
        code, _, err = run_cli(*argv)
        self.assertEqual(code, 2)
        self.assertIn("invalid recipient address", err)

    def test_invalid_sender(self):
        argv = without(SERVICE_ARGS, "--from") + ["--from", "Icinga"]
        code, _, err = run_cli(*argv)
        self.assertEqual(code, 2)
        self.assertIn("invalid sender address", err)


class OptionalArgumentTests(unittest.TestCase):
    OPTIONAL = {
        "--host-display-name": "PostgreSQL primary",
        "--service-display-name": "PostgreSQL database",
        "--address": "10.0.0.10",
        "--address6": "2001:db8::10",
        "--long-output": "line 1\nline 2",
        "--notes": "Main PostgreSQL database",
        "--author": "icingaadmin",
        "--comment": "Working on it",
        "--environment": "PROD",
        "--icingaweb-url": "https://monitoring.example.com/icingaweb2",
        "--duration": "494",
    }

    def test_optional_arguments(self):
        argv = list(SERVICE_ARGS)
        for option, value in self.OPTIONAL.items():
            argv += [option, value]
        _, n = parse(argv)
        self.assertEqual(n.host_display_name, "PostgreSQL primary")
        self.assertEqual(n.service_display_name, "PostgreSQL database")
        self.assertEqual(n.address, "10.0.0.10")
        self.assertEqual(n.address6, "2001:db8::10")
        self.assertEqual(n.long_output, "line 1\nline 2")
        self.assertEqual(n.notes, "Main PostgreSQL database")
        self.assertEqual(n.author, "icingaadmin")
        self.assertEqual(n.comment, "Working on it")
        self.assertEqual(n.environment, "PROD")
        self.assertEqual(n.icingaweb_url, "https://monitoring.example.com/icingaweb2")
        self.assertEqual(n.duration, 494)

    def test_empty_optional_values(self):
        argv = list(SERVICE_ARGS)
        for option in self.OPTIONAL:
            if option != "--duration":
                argv += [option, ""]
        _, n = parse(argv)
        for option in self.OPTIONAL:
            if option == "--duration":
                continue
            attr = option.removeprefix("--").replace("-", "_")
            with self.subTest(option=option):
                self.assertIsNone(getattr(n, attr))

    def test_absent_optional_values(self):
        _, n = parse(SERVICE_ARGS)
        self.assertIsNone(n.environment)
        self.assertIsNone(n.duration)
        self.assertIsNone(n.icingaweb_url)


class TagArgumentTests(unittest.TestCase):
    def test_no_tags(self):
        _, n = parse(SERVICE_ARGS)
        self.assertEqual(n.tags, ())

    def test_repeatable_tags(self):
        _, n = parse(SERVICE_ARGS + [
            "--tag", "Location=DC Milano",
            "--tag", "Team=DBA",
            "--tag", "Customer=ACME",
        ])
        self.assertEqual(
            n.tags,
            (Tag("Location", "DC Milano"), Tag("Team", "DBA"), Tag("Customer", "ACME")),
        )

    def test_split_on_first_equal_sign(self):
        _, n = parse(SERVICE_ARGS + ["--tag", "Query=a=b"])
        self.assertEqual(n.tags, (Tag("Query", "a=b"),))

    def test_empty_value_is_silently_omitted(self):
        with self.assertNoLogs("icinga_modern_notifications", level="WARNING"):
            _, n = parse(SERVICE_ARGS + ["--tag", "Location=", "--tag", "Team=  "])
        self.assertEqual(n.tags, ())

    def test_malformed_tags_are_ignored_with_warning(self):
        argv = SERVICE_ARGS + ["--tag", "DC Milano", "--tag", "=DBA", "--tag", "Rack=B4"]
        with self.assertLogs("icinga_modern_notifications.cli", level="WARNING") as logs:
            _, n = parse(argv)
        self.assertEqual(n.tags, (Tag("Rack", "B4"),))
        self.assertEqual(len(logs.records), 2)
        self.assertIn("ignoring malformed tag 'DC Milano'", logs.output[0])
        self.assertIn("ignoring malformed tag '=DBA'", logs.output[1])

    def test_long_malformed_tag_is_truncated_in_log(self):
        with self.assertLogs("icinga_modern_notifications.cli", level="WARNING") as logs:
            parse(SERVICE_ARGS + ["--tag", "x" * 500])
        self.assertLess(len(logs.output[0]), 200)

    def test_malformed_tag_does_not_block_notification(self):
        code, out, err = run_cli(*SERVICE_ARGS, "--tag", "broken", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("multipart/alternative", out)
        self.assertIn("warning: ignoring malformed tag 'broken'", err)

    def test_tags_on_host_notifications(self):
        _, n = parse(HOST_ARGS + ["--tag", "Location=DC Milano"])
        self.assertEqual(n.tags, (Tag("Location", "DC Milano"),))

    def test_help_mentions_tag(self):
        _, out, _ = run_cli("mail", "service", "--help")
        self.assertIn("--tag LABEL=VALUE", out)


class ValidationTests(unittest.TestCase):
    def test_invalid_host_state(self):
        argv = without(HOST_ARGS, "--state") + ["--state", "CRITICAL"]
        code, _, err = run_cli(*argv)
        self.assertEqual(code, 2)
        self.assertIn("invalid host state", err)

    def test_invalid_service_state(self):
        argv = without(SERVICE_ARGS, "--state") + ["--state", "DOWN"]
        code, _, err = run_cli(*argv)
        self.assertEqual(code, 2)
        self.assertIn("invalid service state", err)

    def test_state_case_insensitive(self):
        _, n = parse(without(SERVICE_ARGS, "--state") + ["--state", "warning"])
        self.assertIs(n.state, State.WARNING)

    def test_invalid_numbers(self):
        for option, value in (
            ("--timestamp", "yesterday"),
            ("--timestamp", "-5"),
            ("--duration", "abc"),
            ("--duration", "-1"),
        ):
            with self.subTest(option=option, value=value):
                argv = list(SERVICE_ARGS)
                if option in argv:
                    argv = without(argv, option)
                err = parse_error(argv + [option, value])
                self.assertIn(option, err)


class TemplateDirDefaultTests(unittest.TestCase):
    def test_default_template_dir_is_not_cwd(self):
        args = build_parser().parse_args(SERVICE_ARGS)
        repo_root = Path(__file__).resolve().parent.parent
        self.assertEqual(args.default_template_dir, repo_root)

    def test_default_template_dir_override(self):
        args = build_parser(Path("/opt/imn")).parse_args(SERVICE_ARGS)
        self.assertEqual(args.default_template_dir, Path("/opt/imn"))


if __name__ == "__main__":
    unittest.main()
