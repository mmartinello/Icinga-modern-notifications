"""Tests for email subject construction."""

import unittest

from icinga_modern_notifications.channels.mail.subject import build_subject
from icinga_modern_notifications.model import Notification, ObjectKind


def host(**overrides):
    values = dict(
        kind=ObjectKind.HOST,
        notification_type="Problem",
        state="DOWN",
        host="postgres01",
        output="PING CRITICAL",
        timestamp=0,
    )
    values.update(overrides)
    return Notification(**values)


def service(**overrides):
    values = dict(
        kind=ObjectKind.SERVICE,
        notification_type="Problem",
        state="CRITICAL",
        host="postgres01",
        service="PostgreSQL",
        output="CRITICAL",
        timestamp=0,
    )
    values.update(overrides)
    return Notification(**values)


class HostSubjectTests(unittest.TestCase):
    def test_host_down_with_environment(self):
        self.assertEqual(
            build_subject(host(environment="PROD")),
            "🔴 [ICINGA][DOWN][PROD] postgres01",
        )

    def test_host_down_without_environment(self):
        self.assertEqual(build_subject(host()), "🔴 [ICINGA][DOWN] postgres01")

    def test_host_down_with_empty_environment(self):
        self.assertEqual(
            build_subject(host(environment="")), "🔴 [ICINGA][DOWN] postgres01"
        )

    def test_host_recovery_with_environment(self):
        self.assertEqual(
            build_subject(host(notification_type="Recovery", state="UP", environment="PROD")),
            "🟢 [ICINGA][RECOVERY][PROD] postgres01",
        )

    def test_host_recovery_without_environment(self):
        self.assertEqual(
            build_subject(host(notification_type="Recovery", state="UP")),
            "🟢 [ICINGA][RECOVERY] postgres01",
        )


class ServiceSubjectTests(unittest.TestCase):
    def test_service_critical_with_environment(self):
        self.assertEqual(
            build_subject(service(environment="PROD")),
            "🔴 [ICINGA][CRITICAL][PROD] postgres01 / PostgreSQL",
        )

    def test_service_critical_without_environment(self):
        self.assertEqual(
            build_subject(service()),
            "🔴 [ICINGA][CRITICAL] postgres01 / PostgreSQL",
        )

    def test_service_warning(self):
        self.assertEqual(
            build_subject(service(state="WARNING")),
            "🟠 [ICINGA][WARNING] postgres01 / PostgreSQL",
        )

    def test_service_unknown(self):
        self.assertEqual(
            build_subject(service(state="UNKNOWN", environment="TEST")),
            "🟣 [ICINGA][UNKNOWN][TEST] postgres01 / PostgreSQL",
        )

    def test_service_recovery_with_environment(self):
        self.assertEqual(
            build_subject(service(notification_type="Recovery", state="OK", environment="PROD")),
            "🟢 [ICINGA][RECOVERY][PROD] postgres01 / PostgreSQL",
        )

    def test_service_recovery_without_environment(self):
        self.assertEqual(
            build_subject(service(notification_type="Recovery", state="OK")),
            "🟢 [ICINGA][RECOVERY] postgres01 / PostgreSQL",
        )

    def test_display_names_are_not_used(self):
        n = service(host_display_name="DB primary", service_display_name="Postgres DB")
        self.assertEqual(build_subject(n), "🔴 [ICINGA][CRITICAL] postgres01 / PostgreSQL")

    def test_no_line_breaks(self):
        n = service(service="Postgre\nSQL", environment="PR\r\nOD")
        self.assertNotIn("\n", build_subject(n))
        self.assertNotIn("\r", build_subject(n))


if __name__ == "__main__":
    unittest.main()
