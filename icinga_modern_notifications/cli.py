"""Command-line interface.

The command line is organised as ``<channel> <object kind> [OPTIONS]``, for
example ``icinga-modern-notifications mail service ...``. Channels are
discovered from :func:`~icinga_modern_notifications.channels.available_channels`
so that new channels can be added without changing this module.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import PROJECT_NAME, __version__
from .channels import available_channels
from .errors import ExitCode, NotificationError

PROG = "icinga-modern-notifications"

#: Object kinds that can be notified, with their sub-command help.
OBJECT_KINDS = {
    "host": "notify about a host",
    "service": "notify about a service",
}


def default_template_dir() -> Path:
    """Return the directory containing the application (not the CWD)."""
    return Path(__file__).resolve().parent.parent


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
                kind, help=kind_help, description=kind_help.capitalize()
            )
            channel.add_arguments(kind_parser)
            kind_parser.set_defaults(channel_impl=channel)

    return parser


def main(
    argv: Sequence[str] | None = None, default_template_dir: Path | None = None
) -> int:
    """Run the application and return the process exit code."""
    parser = build_parser(default_template_dir)
    args = parser.parse_args(argv)

    try:
        args.channel_impl.run(args)
    except NotificationError as exc:
        print(f"{PROG}: error: {exc}", file=sys.stderr)
        return int(exc.exit_code)
    except KeyboardInterrupt:
        print(f"{PROG}: interrupted", file=sys.stderr)
        return int(ExitCode.RUNTIME_ERROR)
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        print(f"{PROG}: unexpected error: {exc}", file=sys.stderr)
        return int(ExitCode.RUNTIME_ERROR)

    return int(ExitCode.SUCCESS)
