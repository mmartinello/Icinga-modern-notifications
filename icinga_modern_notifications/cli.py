"""Command-line interface.

The command line is organised as ``<channel> <object kind> [OPTIONS]``, for
example ``icinga-modern-notifications mail service ...``. Channels are
discovered from :func:`~icinga_modern_notifications.channels.available_channels`
so that new channels can be added without changing this module; the options
describing the Icinga object are shared by every channel.
"""

from __future__ import annotations

import argparse
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from . import PROJECT_NAME, __version__
from .channels import available_channels
from .errors import ExitCode, NotificationError, ValidationError
from .icingaweb import DEFAULT_MODULE, ROUTES
from .log import add_logging_arguments, configure_logging, get_logger
from .model import Notification, ObjectKind, Tag, VALID_STATES
from .utils import parse_duration, parse_timestamp

PROG = "icinga-modern-notifications"

log = get_logger("cli")

#: Object kinds that can be notified, with their sub-command help.
OBJECT_KINDS = {
    ObjectKind.HOST: "notify about a host",
    ObjectKind.SERVICE: "notify about a service",
}


def default_template_dir() -> Path:
    """Return the directory containing the application (not the CWD)."""
    return Path(__file__).resolve().parent.parent


def _argparse_type(parser: Callable[[str], object]) -> Callable[[str], object]:
    """Adapt a parser raising ValueError into an argparse type function."""

    def convert(value: str) -> object:
        try:
            return parser(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(str(exc)) from None

    convert.__name__ = parser.__name__.removeprefix("parse_")
    return convert


def add_notification_arguments(
    parser: argparse.ArgumentParser, kind: ObjectKind
) -> None:
    """Add the channel-independent options describing the Icinga object."""
    states = ", ".join(state.value for state in VALID_STATES[kind])

    required = parser.add_argument_group("required notification options")
    required.add_argument(
        "--notification-type",
        required=True,
        metavar="TYPE",
        help="Icinga notification type, e.g. Problem, Recovery, Acknowledgement",
    )
    required.add_argument(
        "--state", required=True, help=f"current {kind} state ({states})"
    )
    required.add_argument("--host", required=True, help="technical Icinga host name")
    if kind is ObjectKind.SERVICE:
        required.add_argument(
            "--service", required=True, help="technical Icinga service name"
        )
    required.add_argument(
        "--output", required=True, metavar="TEXT", help="plugin/check output"
    )

    optional = parser.add_argument_group("optional notification options")
    optional.add_argument(
        "--host-display-name", metavar="NAME", help="human-readable host name"
    )
    if kind is ObjectKind.SERVICE:
        optional.add_argument(
            "--service-display-name",
            metavar="NAME",
            help="human-readable service name",
        )
    optional.add_argument("--address", help="host IPv4 or primary address")
    optional.add_argument("--address6", metavar="ADDRESS", help="host IPv6 address")
    optional.add_argument("--long-output", metavar="TEXT", help="extended plugin output")
    optional.add_argument(
        "--notes", metavar="TEXT", help=f"{kind} notes (plain text)"
    )
    optional.add_argument("--author", help="notification author")
    optional.add_argument("--comment", help="notification comment")
    optional.add_argument(
        "--environment",
        metavar="ENV",
        help="environment identifier, e.g. PROD (omitted when empty)",
    )
    optional.add_argument(
        "--icingaweb-url", metavar="URL", help="base URL of Icinga Web"
    )
    optional.add_argument(
        "--icingaweb-module",
        choices=sorted(ROUTES),
        default=DEFAULT_MODULE,
        help="Icinga Web module used to build object links (default: %(default)s)",
    )
    optional.add_argument(
        "--timestamp",
        type=_argparse_type(parse_timestamp),
        help="Unix timestamp of the event (default: now)",
    )
    optional.add_argument(
        "--duration",
        metavar="SECONDS",
        type=_argparse_type(parse_duration),
        help="event/problem duration in seconds",
    )
    optional.add_argument(
        "--tag",
        dest="tags",
        action="append",
        default=[],
        metavar="LABEL=VALUE",
        help="free-form tag shown next to the environment, e.g. 'Location=DC Milano' "
        "(repeatable; tags with an empty value are omitted)",
    )


def parse_tags(values: Sequence[str]) -> list[Tag]:
    """Parse ``LABEL=VALUE`` strings, splitting on the first ``=``.

    Tags are decorative: a malformed tag is logged and skipped so that it can
    never prevent an alert from being delivered.
    """
    tags = []
    for value in values:
        label, separator, tag_value = value.partition("=")
        try:
            if not separator:
                raise ValidationError("missing '='")
            tags.append(Tag(label, tag_value))
        except ValidationError as exc:
            shown = value if len(value) <= 80 else value[:77] + "..."
            log.warning("ignoring malformed tag %r (expected LABEL=VALUE): %s", shown, exc)
    return tags


def build_parser(template_dir: Path | None = None) -> argparse.ArgumentParser:
    """Build the complete argument parser."""
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=f"{PROJECT_NAME}: modern, extensible and responsive "
        "notifications for Icinga 2.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.set_defaults(default_template_dir=template_dir or default_template_dir())

    channel_parsers = parser.add_subparsers(
        dest="channel", metavar="CHANNEL", required=True
    )
    for channel in available_channels():
        channel_parser = channel_parsers.add_parser(
            channel.name, help=channel.help, description=channel.help.capitalize()
        )
        kind_parsers = channel_parser.add_subparsers(
            dest="kind", metavar="KIND", required=True
        )
        for kind, kind_help in OBJECT_KINDS.items():
            kind_parser = kind_parsers.add_parser(
                kind.value, help=kind_help, description=kind_help.capitalize()
            )
            add_notification_arguments(kind_parser, kind)
            channel.add_arguments(kind_parser)
            add_logging_arguments(kind_parser)
            kind_parser.set_defaults(channel_impl=channel, kind=kind)

    return parser


def notification_from_args(args: argparse.Namespace) -> Notification:
    """Build the normalised notification model from parsed arguments."""
    return Notification(
        kind=args.kind,
        notification_type=args.notification_type,
        state=args.state,
        host=args.host,
        output=args.output,
        timestamp=args.timestamp if args.timestamp is not None else time.time(),
        host_display_name=args.host_display_name,
        address=args.address,
        address6=args.address6,
        service=getattr(args, "service", None),
        service_display_name=getattr(args, "service_display_name", None),
        long_output=args.long_output,
        notes=args.notes,
        environment=args.environment,
        author=args.author,
        comment=args.comment,
        duration=args.duration,
        icingaweb_url=args.icingaweb_url,
        tags=tuple(parse_tags(args.tags)),
    )


def main(
    argv: Sequence[str] | None = None, default_template_dir: Path | None = None
) -> int:
    """Run the application and return the process exit code."""
    parser = build_parser(default_template_dir)
    args = parser.parse_args(argv)
    logger = configure_logging(
        verbose=args.verbose, debug=args.debug, syslog=args.syslog
    )

    try:
        notification = notification_from_args(args)
        logger.debug(
            "%s notification: type=%s state=%s object=%r",
            notification.kind,
            notification.notification_type,
            notification.state,
            notification.object_name,
        )
        args.channel_impl.run(notification, args)
    except NotificationError as exc:
        logger.error("%s", exc)
        return int(exc.exit_code)
    except KeyboardInterrupt:
        logger.error("interrupted")
        return int(ExitCode.RUNTIME_ERROR)
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        logger.error("unexpected error: %s: %s", type(exc).__name__, exc)
        logger.debug("traceback of the unexpected error", exc_info=True)
        return int(ExitCode.RUNTIME_ERROR)

    return int(ExitCode.SUCCESS)
