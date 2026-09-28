"""Tests for the channel-independent notification model."""

import unittest

from icinga_modern_notifications.errors import ValidationError
from icinga_modern_notifications.model import (
    DisplayStatus,
    Notification,
    ObjectKind,
    State,
    STATUS_EMOJI,
)


def host_notification(**overrides) -> Notification:
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


def service_notification(**overrides) -> Notification:
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


class HostNotificationTests(unittest.TestCase):
    def test_host_problem(self):
        n = host_notification()
        self.assertIs(n.kind, ObjectKind.HOST)
        self.assertFalse(n.is_service)
        self.assertEqual(n.notification_type, "PROBLEM")
        self.assertTrue(n.is_problem)
        self.assertFalse(n.is_recovery)
        self.assertIs(n.state, State.DOWN)
        self.assertIs(n.display_status, DisplayStatus.DOWN)
        self.assertEqual(n.emoji, "🔴")
        self.assertEqual(n.object_name, "postgres01")

    def test_host_recovery(self):
        n = host_notification(notification_type="Recovery", state="UP")
        self.assertTrue(n.is_recovery)
        self.assertFalse(n.is_problem)
        self.assertIs(n.state, State.UP)
        self.assertIs(n.display_status, DisplayStatus.RECOVERY)
        self.assertEqual(n.emoji, "🟢")

    def test_host_rejects_service_state(self):
        with self.assertRaises(ValidationError):
            host_notification(state="CRITICAL")

    def test_host_rejects_service(self):
        with self.assertRaises(ValidationError):
            host_notification(service="PostgreSQL")

    def test_host_title(self):
        self.assertEqual(host_notification().host_title, "postgres01")
        n = host_notification(host_display_name="PostgreSQL primary")
        self.assertEqual(n.host_title, "PostgreSQL primary")


class ServiceNotificationTests(unittest.TestCase):
    def test_states(self):
        expected = {
            "WARNING": ("🟠", DisplayStatus.WARNING),
            "CRITICAL": ("🔴", DisplayStatus.CRITICAL),
            "UNKNOWN": ("🟣", DisplayStatus.UNKNOWN),
        }
        for state, (emoji, status) in expected.items():
            with self.subTest(state=state):
                n = service_notification(state=state)
                self.assertIs(n.display_status, status)
                self.assertEqual(n.emoji, emoji)

    def test_service_recovery(self):
        n = service_notification(notification_type="Recovery", state="OK")
        self.assertIs(n.state, State.OK)
        self.assertIs(n.display_status, DisplayStatus.RECOVERY)
        self.assertEqual(n.emoji, "🟢")

    def test_object_name(self):
        self.assertEqual(service_notification().object_name, "postgres01 / PostgreSQL")

    def test_service_required(self):
        with self.assertRaises(ValidationError):
            service_notification(service="")

    def test_service_rejects_host_state(self):
        with self.assertRaises(ValidationError):
            service_notification(state="DOWN")

    def test_service_title(self):
        self.assertEqual(service_notification().service_title, "PostgreSQL")
        n = service_notification(service_display_name="PostgreSQL main database")
        self.assertEqual(n.service_title, "PostgreSQL main database")


class NormalizationTests(unittest.TestCase):
    def test_state_is_case_insensitive(self):
        self.assertIs(service_notification(state=" critical ").state, State.CRITICAL)
        self.assertIs(host_notification(state="down").state, State.DOWN)

    def test_notification_type_is_normalized(self):
        self.assertEqual(
            service_notification(notification_type="Downtime Start").notification_type,
            "DOWNTIMESTART",
        )

    def test_notification_type_is_not_restricted(self):
        n = service_notification(notification_type="Acknowledgement")
        self.assertEqual(n.notification_type, "ACKNOWLEDGEMENT")
        self.assertEqual(n.notification_type_label, "Acknowledgement")
        self.assertIs(n.display_status, DisplayStatus.CRITICAL)
        n = service_notification(notification_type="SomethingNew")
        self.assertEqual(n.notification_type_label, "Somethingnew")

    def test_empty_notification_type_rejected(self):
        with self.assertRaises(ValidationError):
            service_notification(notification_type="  ")

    def test_empty_host_rejected(self):
        with self.assertRaises(ValidationError):
            host_notification(host=" ")

    def test_negative_numbers_rejected(self):
        with self.assertRaises(ValidationError):
            host_notification(timestamp=-1)
        with self.assertRaises(ValidationError):
            host_notification(duration=-1)


class EnvironmentTests(unittest.TestCase):
    def test_environment_present(self):
        self.assertEqual(service_notification(environment="PROD").environment, "PROD")
        self.assertEqual(service_notification(environment=" PROD ").environment, "PROD")

    def test_environment_absent(self):
        self.assertIsNone(service_notification().environment)
        self.assertIsNone(service_notification(environment="").environment)
        self.assertIsNone(service_notification(environment="   ").environment)


class OptionalFieldsTests(unittest.TestCase):
    def test_empty_optional_values_become_none(self):
        n = service_notification(
            host_display_name="",
            address=" ",
            address6="",
            service_display_name="",
            long_output="\n",
            notes="",
            author="",
            comment="",
            icingaweb_url="",
        )
        for name in (
            "host_display_name",
            "address",
            "address6",
            "service_display_name",
            "long_output",
            "notes",
            "author",
            "comment",
            "icingaweb_url",
        ):
            with self.subTest(field=name):
                self.assertIsNone(getattr(n, name))


class EmojiMappingTests(unittest.TestCase):
    def test_every_display_status_has_an_emoji(self):
        for status in DisplayStatus:
            self.assertIn(status, STATUS_EMOJI)


if __name__ == "__main__":
    unittest.main()
