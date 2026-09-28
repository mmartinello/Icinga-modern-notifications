"""Tests for the sendmail transport."""

import subprocess
import unittest
from pathlib import Path
from unittest import mock

from icinga_modern_notifications.channels.mail.transport import SendmailTransport
from icinga_modern_notifications.errors import DeliveryError, ExitCode

MESSAGE = b"Subject: test\n\nbody\n"


def completed(returncode=0, stderr=b""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=b"", stderr=stderr)


class SendmailTransportTests(unittest.TestCase):
    def setUp(self):
        self.transport = SendmailTransport(Path("/usr/sbin/sendmail"))

    @mock.patch("subprocess.run", return_value=completed())
    def test_success(self, run):
        self.transport.send(MESSAGE, ["admin@example.com", "NOC <noc@example.com>"])
        run.assert_called_once()
        args, kwargs = run.call_args
        self.assertEqual(
            args[0],
            ["/usr/sbin/sendmail", "-oi", "--", "admin@example.com", "noc@example.com"],
        )
        self.assertEqual(kwargs["input"], MESSAGE)
        self.assertIs(kwargs["shell"], False)

    @mock.patch("subprocess.run", side_effect=FileNotFoundError())
    def test_executable_missing(self, run):
        with self.assertRaises(DeliveryError) as ctx:
            self.transport.send(MESSAGE, ["admin@example.com"])
        self.assertIn("not found", str(ctx.exception))
        self.assertEqual(ctx.exception.exit_code, ExitCode.DELIVERY_ERROR)

    @mock.patch("subprocess.run", side_effect=PermissionError())
    def test_executable_not_executable(self, run):
        with self.assertRaises(DeliveryError) as ctx:
            self.transport.send(MESSAGE, ["admin@example.com"])
        self.assertIn("not executable", str(ctx.exception))

    @mock.patch("subprocess.run", return_value=completed(75, b"temporary failure\n"))
    def test_non_zero_exit(self, run):
        with self.assertRaises(DeliveryError) as ctx:
            self.transport.send(MESSAGE, ["admin@example.com"])
        self.assertIn("exited with status 75", str(ctx.exception))
        self.assertIn("temporary failure", str(ctx.exception))

    @mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("sendmail", 60))
    def test_timeout(self, run):
        with self.assertRaises(DeliveryError) as ctx:
            self.transport.send(MESSAGE, ["admin@example.com"])
        self.assertIn("did not complete", str(ctx.exception))

    @mock.patch("subprocess.run")
    def test_no_recipients(self, run):
        with self.assertRaises(DeliveryError):
            self.transport.send(MESSAGE, [])
        run.assert_not_called()

    def test_recipient_starting_with_dash_is_not_an_option(self):
        command = self.transport.command(["-bi@example.com"])
        self.assertEqual(command.index("--"), 2)
        self.assertEqual(command[-1], "-bi@example.com")

    def test_real_executable(self):
        """Run a real (fake) sendmail script to exercise the subprocess path."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp, "out.eml")
            script = Path(tmp, "sendmail")
            script.write_text(f"#!/bin/sh\ncat > '{out}'\necho \"$@\" > '{out}.args'\n")
            script.chmod(0o755)
            SendmailTransport(script).send(MESSAGE, ["admin@example.com"])
            self.assertEqual(out.read_bytes(), MESSAGE)
            self.assertEqual(Path(f"{out}.args").read_text().strip(), "-oi -- admin@example.com")


if __name__ == "__main__":
    unittest.main()
