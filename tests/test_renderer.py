"""Tests for the mail renderer and templates."""

import tempfile
import unittest
from pathlib import Path

from icinga_modern_notifications.channels.mail.renderer import MailRenderer
from icinga_modern_notifications.errors import TemplateError
from icinga_modern_notifications.icingaweb import object_url
from icinga_modern_notifications.model import Notification, ObjectKind
from icinga_modern_notifications.utils import format_timestamp

TEMPLATE_DIR = Path(__file__).resolve().parent.parent
PLACEHOLDERS = ("None", "N/A", "Unknown")


def service(**overrides):
    values = dict(
        kind=ObjectKind.SERVICE,
        notification_type="Problem",
        state="CRITICAL",
        host="postgres01",
        service="PostgreSQL",
        output="CRITICAL - PostgreSQL is not accepting connections",
        timestamp=1790000000,
    )
    values.update(overrides)
    return Notification(**values)


def host(**overrides):
    values = dict(
        kind=ObjectKind.HOST,
        notification_type="Problem",
        state="DOWN",
        host="postgres01",
        output="PING CRITICAL - Packet loss = 100%",
        timestamp=1790000000,
    )
    values.update(overrides)
    return Notification(**values)


FULL = dict(
    host_display_name="PostgreSQL primary",
    service_display_name="PostgreSQL database",
    address="10.0.0.10",
    address6="2001:db8::10",
    long_output="connection refused\nretrying",
    notes="Main PostgreSQL database",
    environment="PROD",
    author="icingaadmin",
    comment="Working on it",
    duration=974,
    icingaweb_url="https://monitoring.example.com/icingaweb2",
)


class RendererTestCase(unittest.TestCase):
    renderer = MailRenderer(TEMPLATE_DIR)

    def context(self, notification):
        return MailRenderer.context(
            notification, "subject", object_url(notification)
        )

    def text(self, notification):
        return self.renderer.render_text(self.context(notification))


class TextTemplateTests(RendererTestCase):
    def test_full_service_notification(self):
        text = self.text(service(**FULL))
        self.assertTrue(text.startswith("🔴 CRITICAL [PROD]\n\n"))
        for expected in (
            "PostgreSQL database on PostgreSQL primary",
            "Output:\nCRITICAL - PostgreSQL is not accepting connections\n",
            "Notification: Problem\n",
            "Host: PostgreSQL primary (postgres01)\n",
            "Service: PostgreSQL database (PostgreSQL)\n",
            "Environment: PROD\n",
            "State: CRITICAL\n",
            "Address: 10.0.0.10\n",
            "IPv6 address: 2001:db8::10\n",
            f"Since: {format_timestamp(1790000000)}\n",
            "Duration: 16m 14s\n",
            "Additional output:\nconnection refused\nretrying\n",
            "Notes:\nMain PostgreSQL database\n",
            "Author: icingaadmin\n",
            "Comment:\nWorking on it\n",
            "Icinga Web:\nhttps://monitoring.example.com/icingaweb2/icingadb/service?"
            "name=PostgreSQL&host.name=postgres01\n",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

    def test_minimal_notification_omits_optional_fields(self):
        text = self.text(host())
        self.assertTrue(text.startswith("🔴 DOWN\n\npostgres01\n\n"))
        for absent in (
            "Environment",
            "Address",
            "IPv6",
            "Duration",
            "Additional output",
            "Notes",
            "Author",
            "Comment",
            "Icinga Web",
            "Service",
            "[",
        ) + PLACEHOLDERS:
            with self.subTest(absent=absent):
                self.assertNotIn(absent, text)
        self.assertNotIn("\n\n\n", text)

    def test_empty_environment_is_omitted(self):
        text = self.text(service(environment=""))
        self.assertNotIn("Environment", text)
        self.assertTrue(text.startswith("🔴 CRITICAL\n"))

    def test_zero_duration_is_rendered(self):
        self.assertIn("Duration: 0s\n", self.text(service(duration=0)))

    def test_recovery(self):
        text = self.text(service(notification_type="Recovery", state="OK"))
        self.assertTrue(text.startswith("🟢 RECOVERY\n"))
        self.assertIn("State: OK\n", text)

    def test_text_is_not_escaped(self):
        text = self.text(service(output="<b>a & b</b>", notes="x < y"))
        self.assertIn("<b>a & b</b>", text)
        self.assertIn("x < y", text)

    def test_unicode(self):
        text = self.text(service(notes="Città già è ✓ 🚀"))
        self.assertIn("Città già è ✓ 🚀", text)


class TemplateErrorTests(unittest.TestCase):
    def test_missing_template_dir(self):
        with self.assertRaises(TemplateError) as ctx:
            MailRenderer(Path("/nonexistent/template/dir"))
        self.assertIn("does not exist", str(ctx.exception))

    def test_missing_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            renderer = MailRenderer(Path(tmp))
            with self.assertRaises(TemplateError) as ctx:
                renderer.render_text(MailRenderer.context(service(), "s", None))
            self.assertIn("not found", str(ctx.exception))

    def test_syntax_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "notification.txt.j2").write_text("{% if %}")
            renderer = MailRenderer(Path(tmp))
            with self.assertRaises(TemplateError) as ctx:
                renderer.render_text(MailRenderer.context(service(), "s", None))
            self.assertIn("syntax error", str(ctx.exception))

    def test_undefined_variable(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "notification.txt.j2").write_text("{{ missing.value }}")
            renderer = MailRenderer(Path(tmp))
            with self.assertRaises(TemplateError) as ctx:
                renderer.render_text(MailRenderer.context(service(), "s", None))
            self.assertIn("cannot render", str(ctx.exception))

    def test_undecodable_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "notification.txt.j2").write_bytes(b"\xff\xfe\x00bad")
            renderer = MailRenderer(Path(tmp))
            with self.assertRaises(TemplateError):
                renderer.render_text(MailRenderer.context(service(), "s", None))


if __name__ == "__main__":
    unittest.main()
