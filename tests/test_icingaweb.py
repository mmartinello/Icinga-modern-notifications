"""Tests for Icinga Web link generation."""

import unittest

from icinga_modern_notifications.errors import ValidationError
from icinga_modern_notifications.icingaweb import object_url
from icinga_modern_notifications.model import Notification, ObjectKind

BASE = "https://monitoring.example.com/icingaweb2"


def notification(kind=ObjectKind.SERVICE, **overrides):
    values = dict(
        kind=kind,
        notification_type="Problem",
        state="CRITICAL" if kind is ObjectKind.SERVICE else "DOWN",
        host="postgres01",
        service="PostgreSQL" if kind is ObjectKind.SERVICE else None,
        output="CRITICAL",
        timestamp=0,
        icingaweb_url=BASE,
    )
    values.update(overrides)
    return Notification(**values)


class ObjectUrlTests(unittest.TestCase):
    def test_no_base_url(self):
        self.assertIsNone(object_url(notification(icingaweb_url=None)))
        self.assertIsNone(object_url(notification(icingaweb_url="")))

    def test_icingadb_host(self):
        self.assertEqual(
            object_url(notification(ObjectKind.HOST)),
            f"{BASE}/icingadb/host?name=postgres01",
        )

    def test_icingadb_service(self):
        self.assertEqual(
            object_url(notification()),
            f"{BASE}/icingadb/service?name=PostgreSQL&host.name=postgres01",
        )

    def test_monitoring_module(self):
        self.assertEqual(
            object_url(notification(ObjectKind.HOST), "monitoring"),
            f"{BASE}/monitoring/host/show?host=postgres01",
        )
        self.assertEqual(
            object_url(notification(), "monitoring"),
            f"{BASE}/monitoring/service/show?host=postgres01&service=PostgreSQL",
        )

    def test_names_are_encoded(self):
        url = object_url(notification(host="db&1 é", service="Disk /var?x=1#y"))
        self.assertEqual(
            url,
            f"{BASE}/icingadb/service?name=Disk%20%2Fvar%3Fx%3D1%23y"
            "&host.name=db%261%20%C3%A9",
        )

    def test_trailing_slash_is_removed(self):
        url = object_url(notification(ObjectKind.HOST, icingaweb_url=BASE + "/"))
        self.assertEqual(url, f"{BASE}/icingadb/host?name=postgres01")

    def test_unsupported_module(self):
        with self.assertRaises(ValidationError):
            object_url(notification(), "nagios")


class BaseUrlValidationTests(unittest.TestCase):
    def test_invalid_base_urls(self):
        for url in (
            "javascript:alert(1)",
            "monitoring.example.com",
            "ftp://monitoring.example.com",
            "https://",
            "https://example.com/?a=b",
            "https://example.com/#x",
            "https://exa mple.com",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValidationError):
                    notification(icingaweb_url=url)


if __name__ == "__main__":
    unittest.main()
