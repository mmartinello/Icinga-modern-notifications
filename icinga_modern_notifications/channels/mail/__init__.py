"""Mail notification channel."""

from __future__ import annotations

import argparse
from pathlib import Path

from ...icingaweb import object_url
from ...model import Notification
from ..base import Channel
from .config import MailSettings
from .message import build_message, message_bytes
from .renderer import MailRenderer
from .subject import build_subject
from .transport import DEFAULT_SENDMAIL_PATH, SendmailTransport


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
        group.add_argument(
            "--template-dir",
            type=Path,
            metavar="PATH",
            help="directory containing notification.txt.j2 and notification.html.j2 "
            "(default: the directory of the executable)",
        )
        group.add_argument(
            "--sendmail-path",
            type=Path,
            default=DEFAULT_SENDMAIL_PATH,
            metavar="PATH",
            help="sendmail-compatible executable (default: %(default)s)",
        )

    def settings(self, args: argparse.Namespace) -> MailSettings:
        """Build the validated mail settings from parsed arguments."""
        return MailSettings.create(args.mail_from, args.mail_to)

    def run(self, notification: Notification, args: argparse.Namespace) -> None:
        """Render the email and hand it over to sendmail.

        Nothing is sent unless validation and rendering of both parts succeed.
        """
        settings = self.settings(args)
        renderer = MailRenderer(args.template_dir or args.default_template_dir)
        subject = build_subject(notification)
        link = object_url(notification, args.icingaweb_module)
        rendered = renderer.render(notification, subject, link)
        message = build_message(rendered, settings)
        SendmailTransport(args.sendmail_path).send(
            message_bytes(message), settings.recipients
        )
