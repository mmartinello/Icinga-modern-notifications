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


class HtmlTemplateTests(RendererTestCase):
    def html(self, notification):
        return self.renderer.render_html(self.context(notification))

    def test_full_service_notification(self):
        html = self.html(service(**FULL))
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        for expected in (
            "🔴 CRITICAL",
            ">PROD</span>",
            "PostgreSQL database",
            "on PostgreSQL primary",
            "CRITICAL - PostgreSQL is not accepting connections",
            ">Environment</td>",
            ">IPv6 address</td>",
            ">16m 14s</td>",
            "connection refused<br>\nretrying",
            "Main PostgreSQL database",
            "<strong>icingaadmin</strong>",
            "Working on it",
            'href="https://monitoring.example.com/icingaweb2/icingadb/service?'
            'name=PostgreSQL&amp;host.name=postgres01"',
            "Open in Icinga Web",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

    def test_minimal_notification_omits_optional_fields(self):
        html = self.html(host())
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
            "href=",
            ">Service<",
        ) + PLACEHOLDERS:
            with self.subTest(absent=absent):
                self.assertNotIn(absent, html)

    def test_empty_environment_leaves_no_trace(self):
        html = self.html(service(environment=""))
        self.assertNotIn("Environment", html)
        self.assertNotIn("letter-spacing:1px;\"></span>", html)

    def test_output_is_escaped(self):
        html = self.html(service(output="<script>alert('x')</script> & <b>bold</b>"))
        self.assertNotIn("<script>", html)
        self.assertNotIn("<b>bold</b>", html)
        self.assertIn("&lt;script&gt;alert(&#39;x&#39;)&lt;/script&gt; &amp; &lt;b&gt;bold&lt;/b&gt;", html)

    def test_notes_are_escaped(self):
        html = self.html(service(notes='<a href="http://evil">click</a>\n**not markdown**'))
        self.assertNotIn('<a href="http://evil">', html)
        self.assertIn("&lt;a href=&#34;http://evil&#34;&gt;click&lt;/a&gt;<br>\n**not markdown**", html)

    def test_long_output_is_escaped(self):
        html = self.html(service(long_output="<img src=x onerror=alert(1)>\r\nnext"))
        self.assertNotIn("<img", html)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;<br>\nnext", html)

    def test_names_and_comment_are_escaped(self):
        html = self.html(service(
            host="h<1>", service="s&2", environment="<PROD>",
            author="<i>me</i>", comment="<u>c</u>",
        ))
        for raw in ("h<1>", "<PROD>", "<i>me</i>", "<u>c</u>"):
            self.assertNotIn(raw, html)
        self.assertIn("s&amp;2", html)

    def test_button_absent_without_url(self):
        html = self.html(service(**{**FULL, "icingaweb_url": None}))
        self.assertNotIn("Open in Icinga Web", html)
        self.assertNotIn("v:roundrect", html)

    def test_recovery_colors_and_heading(self):
        html = self.html(service(notification_type="Recovery", state="OK"))
        self.assertIn("🟢 RECOVERY", html)
        self.assertIn("#2e7d32", html)
        self.assertIn(">OK</td>", html)

    def test_states_have_distinct_headings(self):
        for state, emoji in (("WARNING", "🟠"), ("UNKNOWN", "🟣"), ("CRITICAL", "🔴")):
            with self.subTest(state=state):
                self.assertIn(f"{emoji} {state}", self.html(service(state=state)))

    def test_unicode(self):
        html = self.html(service(notes="Città già è ✓ 🚀"))
        self.assertIn("Città già è ✓ 🚀", html)
        self.assertIn('<meta charset="utf-8">', html)

    def test_no_javascript(self):
        html = self.html(service(**FULL)).lower()
        self.assertNotIn("<script", html)
        self.assertNotIn("javascript:", html)

    def test_render_returns_both_parts(self):
        n = service(**FULL)
        mail = self.renderer.render(n, "the subject", object_url(n))
        self.assertEqual(mail.subject, "the subject")
        self.assertIn("Output:", mail.text)
        self.assertIn("<title>the subject</title>", mail.html)


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

    def test_render_fails_if_html_template_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "notification.txt.j2").write_text("ok")
            renderer = MailRenderer(Path(tmp))
            with self.assertRaises(TemplateError) as ctx:
                renderer.render(service(), "s", None)
            self.assertIn("notification.html.j2", str(ctx.exception))

    def test_html_autoescape_cannot_be_bypassed_by_custom_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "notification.html.j2").write_text("{{ n.output }}")
            renderer = MailRenderer(Path(tmp))
            html = renderer.render_html(
                MailRenderer.context(service(output="<b>x</b>"), "s", None)
            )
            self.assertEqual(html, "&lt;b&gt;x&lt;/b&gt;")

    def test_undecodable_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "notification.txt.j2").write_bytes(b"\xff\xfe\x00bad")
            renderer = MailRenderer(Path(tmp))
            with self.assertRaises(TemplateError):
                renderer.render_text(MailRenderer.context(service(), "s", None))


if __name__ == "__main__":
    unittest.main()
