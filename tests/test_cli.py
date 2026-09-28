"""Tests for the command-line interface."""

import contextlib
import io
import unittest

from icinga_modern_notifications.cli import main


def run_cli(*argv: str) -> tuple[int, str, str]:
    """Run the CLI and return (exit code, stdout, stderr)."""
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = main(list(argv))
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
    return code, stdout.getvalue(), stderr.getvalue()


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


if __name__ == "__main__":
    unittest.main()
