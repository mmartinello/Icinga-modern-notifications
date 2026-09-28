"""Tests for logging behaviour."""

import logging
import logging.handlers
import unittest
from unittest import mock

from icinga_modern_notifications.log import configure_logging, get_logger

from .helpers import SERVICE_ARGS, run_cli

SECRETS = {
    "--output": "SECRET-OUTPUT",
    "--long-output": "SECRET-LONG-OUTPUT",
    "--notes": "SECRET-NOTES",
    "--comment": "SECRET-COMMENT",
}


def argv_with_secrets(*extra):
    argv = [a if a != "CRITICAL - PostgreSQL is not accepting connections" else SECRETS["--output"]
            for a in SERVICE_ARGS]
    for option in ("--long-output", "--notes", "--comment"):
        argv += [option, SECRETS[option]]
    return argv + list(extra)


class LoggingTests(unittest.TestCase):
    def tearDown(self):
        configure_logging()

    def test_success_is_quiet_by_default(self):
        code, out, err = run_cli(*SERVICE_ARGS, "--dry-run", "--dump-eml", "/dev/null")
        self.assertEqual((code, out, err), (0, "", ""))

    def test_verbose_logs_summary(self):
        code, _, err = run_cli(*SERVICE_ARGS, "--dry-run", "--dump-eml", "/dev/null", "--verbose")
        self.assertEqual(code, 0)
        self.assertIn("info: dry run: not sending CRITICAL notification", err)
        self.assertIn("'postgres01 / PostgreSQL' to 1 recipient(s)", err)

    def test_debug_does_not_log_content(self):
        code, _, err = run_cli(*argv_with_secrets("--dry-run", "--dump-eml", "/dev/null", "--debug"))
        self.assertEqual(code, 0)
        self.assertIn("debug:", err)
        for secret in SECRETS.values():
            self.assertNotIn(secret, err)

    def test_errors_go_to_stderr(self):
        code, out, err = run_cli(*SERVICE_ARGS, "--sendmail-path", "/nonexistent/sendmail")
        self.assertEqual(code, 4)
        self.assertEqual(out, "")
        self.assertRegex(err, r"^icinga-modern-notifications: error: sendmail executable")

    def test_unexpected_error_exit_code(self):
        with mock.patch(
            "icinga_modern_notifications.channels.mail.MailChannel.run",
            side_effect=RuntimeError("boom"),
        ):
            code, _, err = run_cli(*SERVICE_ARGS)
        self.assertEqual(code, 1)
        self.assertIn("unexpected error: RuntimeError: boom", err)

    def test_repeated_configuration_does_not_duplicate_handlers(self):
        configure_logging()
        configure_logging(verbose=True)
        self.assertEqual(len(get_logger().handlers), 1)
        self.assertEqual(get_logger().level, logging.INFO)

    @mock.patch("logging.handlers.SysLogHandler")
    def test_syslog_handler(self, handler_cls):
        handler_cls.return_value = logging.NullHandler()
        handler_cls.LOG_USER = logging.handlers.SysLogHandler.LOG_USER
        logger = configure_logging(syslog=True)
        handler_cls.assert_called_once()
        self.assertEqual(len(logger.handlers), 2)

    @mock.patch("logging.handlers.SysLogHandler", side_effect=OSError("no syslog"))
    def test_syslog_failure_is_not_fatal(self, handler_cls):
        code, _, err = run_cli(*SERVICE_ARGS, "--dry-run", "--dump-eml", "/dev/null", "--syslog")
        self.assertEqual(code, 0)
        self.assertIn("warning: cannot connect to syslog: no syslog", err)


if __name__ == "__main__":
    unittest.main()
