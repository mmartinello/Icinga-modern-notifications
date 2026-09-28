"""End-to-end tests running the complete mail pipeline with a fake sendmail."""

import email
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from email import policy
from pathlib import Path

from .helpers import HOST_ARGS, SERVICE_ARGS, run_cli

REPO = Path(__file__).resolve().parent.parent


class FakeSendmailTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.out = self.tmp / "sent.eml"
        self.sendmail = self.make_sendmail(0)

    def make_sendmail(self, status: int, name: str = "sendmail") -> Path:
        script = self.tmp / name
        script.write_text(
            f"#!/bin/sh\ncat > '{self.out}'\necho 'mta says no' >&2\nexit {status}\n"
        )
        script.chmod(0o755)
        return script

    def sent_message(self):
        return email.message_from_bytes(self.out.read_bytes(), policy=policy.default)


class EndToEndTests(FakeSendmailTestCase):
    def test_service_notification_is_sent(self):
        code, out, err = run_cli(
            *SERVICE_ARGS,
            "--to", "noc@example.com",
            "--environment", "PROD",
            "--sendmail-path", str(self.sendmail),
        )
        self.assertEqual((code, out, err), (0, "", ""))
        msg = self.sent_message()
        self.assertEqual(msg["Subject"], "🔴 [ICINGA][CRITICAL][PROD] postgres01 / PostgreSQL")
        self.assertEqual(msg.get_content_type(), "multipart/alternative")
        self.assertEqual(len(msg["To"].addresses), 2)

    def test_host_notification_is_sent(self):
        code, _, _ = run_cli(*HOST_ARGS, "--sendmail-path", str(self.sendmail))
        self.assertEqual(code, 0)
        self.assertEqual(self.sent_message()["Subject"], "🔴 [ICINGA][DOWN] postgres01")

    def test_sendmail_failure_exit_code(self):
        failing = self.make_sendmail(75, "failing-sendmail")
        code, _, err = run_cli(*SERVICE_ARGS, "--sendmail-path", str(failing))
        self.assertEqual(code, 4)
        self.assertIn("exited with status 75: mta says no", err)

    def test_sendmail_missing_exit_code(self):
        code, _, err = run_cli(*SERVICE_ARGS, "--sendmail-path", str(self.tmp / "nope"))
        self.assertEqual(code, 4)
        self.assertIn("not found", err)

    def test_missing_template_dir_sends_nothing(self):
        code, _, err = run_cli(
            *SERVICE_ARGS,
            "--sendmail-path", str(self.sendmail),
            "--template-dir", str(self.tmp / "missing"),
        )
        self.assertEqual(code, 3)
        self.assertIn("template directory", err)
        self.assertFalse(self.out.exists())

    def test_broken_template_sends_nothing(self):
        templates = self.tmp / "templates"
        templates.mkdir()
        (templates / "notification.txt.j2").write_text("ok")
        (templates / "notification.html.j2").write_text("{% for %}")
        code, _, err = run_cli(
            *SERVICE_ARGS,
            "--sendmail-path", str(self.sendmail),
            "--template-dir", str(templates),
        )
        self.assertEqual(code, 3)
        self.assertIn("notification.html.j2", err)
        self.assertFalse(self.out.exists())

    def test_custom_template_dir(self):
        templates = self.tmp / "templates"
        templates.mkdir()
        (templates / "notification.txt.j2").write_text("custom {{ n.host }}")
        (templates / "notification.html.j2").write_text("<p>custom {{ n.host }}</p>")
        code, _, _ = run_cli(
            *SERVICE_ARGS,
            "--sendmail-path", str(self.sendmail),
            "--template-dir", str(templates),
        )
        self.assertEqual(code, 0)
        text, html = self.sent_message().iter_parts()
        self.assertEqual(text.get_content().strip(), "custom postgres01")

    def test_validation_error_sends_nothing(self):
        argv = [a if a != "CRITICAL" else "BROKEN" for a in SERVICE_ARGS]
        code, _, _ = run_cli(*argv, "--sendmail-path", str(self.sendmail))
        self.assertEqual(code, 2)
        self.assertFalse(self.out.exists())


class LauncherTests(FakeSendmailTestCase):
    def test_launcher_uses_its_own_directory_for_templates(self):
        """Run the installed layout from an unrelated working directory."""
        install = self.tmp / "libexec"
        install.mkdir()
        shutil.copy(REPO / "icinga-modern-notifications", install)
        shutil.copytree(REPO / "icinga_modern_notifications", install / "icinga_modern_notifications")
        for name in ("notification.txt.j2", "notification.html.j2"):
            shutil.copy(REPO / name, install)
        link = self.tmp / "bin-link"
        os.symlink(install / "icinga-modern-notifications", link)

        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        result = subprocess.run(
            [sys.executable, str(link), *SERVICE_ARGS, "--sendmail-path", str(self.sendmail)],
            cwd=self.tmp,
            capture_output=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertTrue(self.out.exists())


if __name__ == "__main__":
    unittest.main()
