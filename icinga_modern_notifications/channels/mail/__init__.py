"""Mail notification channel."""

from __future__ import annotations

import argparse

from ...model import Notification
from ..base import Channel
from .config import MailSettings


class MailChannel(Channel):
    """Deliver notifications as multipart plain-text/HTML email."""

    name = "mail"
    help = "send notifications by email"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add mail-specific options."""
        group = parser.add_argument_group("mail options")
        group.add_argument(
            "--from",
            dest="mail_from",
            required=True,
            metavar="ADDRESS",
            help="sender, e.g. 'Icinga <icinga@example.com>'",
        )
        group.add_argument(
            "--to",
            dest="mail_to",
            action="append",
            required=True,
            metavar="ADDRESS",
            help="recipient (repeatable)",
        )

    def settings(self, args: argparse.Namespace) -> MailSettings:
        """Build the validated mail settings from parsed arguments."""
        return MailSettings.create(args.mail_from, args.mail_to)

    def run(self, notification: Notification, args: argparse.Namespace) -> None:
        """Render and deliver the email (not implemented yet)."""
        self.settings(args)
