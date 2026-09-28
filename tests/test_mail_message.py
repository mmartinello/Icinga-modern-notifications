"""Tests for MIME message construction."""

import email
import unittest
from email import policy
from email.header import decode_header, make_header

from icinga_modern_notifications.channels.mail.config import MailSettings
from icinga_modern_notifications.channels.mail.message import (
    build_message,
    message_bytes,
)
from icinga_modern_notifications.channels.mail.renderer import RenderedMail

SUBJECT = "🔴 [ICINGA][CRITICAL][PROD] postgres01 / PostgreSQL"
MAIL = RenderedMail(
    subject=SUBJECT,
    text="🔴 CRITICAL\n\nCittà: è tutto rotto\n",
    html="<!DOCTYPE html><html><body><p>🔴 CRITICAL – Città</p></body></html>\n",
)
SETTINGS = MailSettings.create(
    "IES / Icinga <icinga@example.com>",
    ["admin@example.com", "NOC Team <noc@example.com>"],
)


def parsed():
    raw = message_bytes(build_message(MAIL, SETTINGS))
    return raw, email.message_from_bytes(raw, policy=policy.default)


class MessageTests(unittest.TestCase):
    def test_multipart_alternative_structure(self):
        _, msg = parsed()
        self.assertEqual(msg.get_content_type(), "multipart/alternative")
        parts = list(msg.iter_parts())
        self.assertEqual(
            [p.get_content_type() for p in parts], ["text/plain", "text/html"]
        )

    def test_parts_content(self):
        _, msg = parsed()
        text, html = msg.iter_parts()
        self.assertEqual(text.get_content(), MAIL.text)
        self.assertEqual(html.get_content(), MAIL.html)
        self.assertEqual(text.get_content_charset(), "utf-8")
        self.assertEqual(html.get_content_charset(), "utf-8")

    def test_unicode_subject_is_encoded(self):
        raw, msg = parsed()
        header_block = raw.split(b"\n\n", 1)[0]
        header_block.decode("ascii")  # raw headers must be pure ASCII
        unfolded = header_block.replace(b"\n ", b" ").replace(b"\n\t", b" ")
        raw_subject = [
            line for line in unfolded.split(b"\n") if line.startswith(b"Subject:")
        ][0]
        self.assertIn(b"=?utf-8?", raw_subject)
        decoded = str(make_header(decode_header(raw_subject[len(b"Subject:"):].decode())))
        self.assertEqual(" ".join(decoded.split()), SUBJECT)
        self.assertEqual(msg["Subject"], SUBJECT)

    def test_sender_display_name(self):
        _, msg = parsed()
        self.assertEqual(msg["From"].addresses[0].display_name, "IES / Icinga")
        self.assertEqual(msg["From"].addresses[0].addr_spec, "icinga@example.com")

    def test_multiple_recipients(self):
        _, msg = parsed()
        self.assertEqual(
            [a.addr_spec for a in msg["To"].addresses],
            ["admin@example.com", "noc@example.com"],
        )

    def test_standard_headers(self):
        _, msg = parsed()
        self.assertTrue(msg["Date"])
        self.assertTrue(msg["Message-ID"].endswith("@example.com>"))
        self.assertEqual(msg["MIME-Version"], "1.0")
        self.assertEqual(msg["Auto-Submitted"], "auto-generated")
        self.assertIn("Icinga Modern Notifications", msg["X-Mailer"])

    def test_body_is_ascii_transfer_encoded_or_8bit(self):
        _, msg = parsed()
        for part in msg.iter_parts():
            self.assertIn(
                part["Content-Transfer-Encoding"],
                ("8bit", "quoted-printable", "base64"),
            )


if __name__ == "__main__":
    unittest.main()
