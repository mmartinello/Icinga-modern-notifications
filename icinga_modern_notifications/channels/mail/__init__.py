"""Mail notification channel."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ...errors import NotificationError
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

        dev = parser.add_argument_group("development and troubleshooting")
        dev.add_argument(
            "--dry-run",
            action="store_true",
            help="build the message but never invoke sendmail; the MIME message "
            "is printed to stdout unless a --dump-* option is given",
        )
        dev.add_argument(
            "--dump-html", type=Path, metavar="FILE", help="write the rendered HTML part to FILE"
        )
        dev.add_argument(
            "--dump-text",
            type=Path,
            metavar="FILE",
            help="write the rendered plain-text part to FILE",
        )
        dev.add_argument(
            "--dump-eml",
            type=Path,
            metavar="FILE",
            help="write the complete MIME message (.eml) to FILE",
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
        raw = message_bytes(build_message(rendered, settings))

        dumps = {
            args.dump_html: rendered.html.encode("utf-8"),
            args.dump_text: rendered.text.encode("utf-8"),
            args.dump_eml: raw,
        }
        for path, content in dumps.items():
            if path is not None:
                write_file(path, content)

        if args.dry_run:
            if not any(path is not None for path in dumps):
                write_stdout(raw)
            return

        SendmailTransport(args.sendmail_path).send(raw, settings.recipients)


def write_file(path: Path, content: bytes) -> None:
    """Write a development dump, reporting failures clearly."""
    try:
        path.write_bytes(content)
    except OSError as exc:
        raise NotificationError(f"cannot write {str(path)!r}: {exc.strerror or exc}") from None


def write_stdout(content: bytes) -> None:
    """Write raw bytes to stdout (falls back to text streams, e.g. in tests)."""
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:
        sys.stdout.flush()
        buffer.write(content)
        buffer.flush()
    else:
        sys.stdout.write(content.decode("utf-8", "replace"))
