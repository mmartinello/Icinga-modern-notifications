"""Logging configuration.

Errors and warnings always go to stderr. ``--verbose`` and ``--debug`` lower
the threshold; ``--syslog`` additionally sends records to the local syslog
daemon through :class:`logging.handlers.SysLogHandler`.

Notification content (mail bodies, notes, comments, plugin output) is never
logged: log records only contain metadata such as object names, states,
recipient counts and sizes.
"""

from __future__ import annotations

import argparse
import logging
import logging.handlers
import os
import sys

LOGGER_NAME = "icinga_modern_notifications"
SYSLOG_IDENT = "icinga-modern-notifications"

#: Candidate local syslog sockets (Linux, macOS).
SYSLOG_SOCKETS = ("/dev/log", "/var/run/syslog")


def get_logger(name: str | None = None) -> logging.Logger:
    """Return the application logger or one of its children."""
    return logging.getLogger(f"{LOGGER_NAME}.{name}" if name else LOGGER_NAME)


class _LowercaseLevelFormatter(logging.Formatter):
    """Format records as ``prog: level: message`` like argparse errors."""

    def format(self, record: logging.LogRecord) -> str:
        record.levelname_lower = record.levelname.lower()
        return super().format(record)


def add_logging_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the logging options to a sub-command parser."""
    group = parser.add_argument_group("logging options")
    group.add_argument(
        "-v", "--verbose", action="store_true", help="log informational messages"
    )
    group.add_argument(
        "--debug", action="store_true", help="log debugging metadata (implies --verbose)"
    )
    group.add_argument(
        "--syslog", action="store_true", help="also send log messages to the local syslog"
    )


def _syslog_handler() -> logging.Handler:
    address: str | tuple[str, int] = ("localhost", logging.handlers.SYSLOG_UDP_PORT)
    for socket_path in SYSLOG_SOCKETS:
        if os.path.exists(socket_path):
            address = socket_path
            break
    handler = logging.handlers.SysLogHandler(
        address=address, facility=logging.handlers.SysLogHandler.LOG_USER
    )
    handler.ident = f"{SYSLOG_IDENT}[{os.getpid()}]: "
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    return handler


def configure_logging(
    *, verbose: bool = False, debug: bool = False, syslog: bool = False
) -> logging.Logger:
    """(Re)configure the application logger and return it.

    Existing handlers are replaced, so calling this repeatedly (e.g. in
    tests) never duplicates output.
    """
    logger = get_logger()
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    level = logging.DEBUG if debug else logging.INFO if verbose else logging.WARNING
    logger.setLevel(level)
    logger.propagate = False

    stderr = logging.StreamHandler(sys.stderr)
    stderr.setFormatter(
        _LowercaseLevelFormatter(f"{SYSLOG_IDENT}: %(levelname_lower)s: %(message)s")
    )
    logger.addHandler(stderr)

    if syslog:
        try:
            logger.addHandler(_syslog_handler())
        except OSError as exc:
            logger.warning("cannot connect to syslog: %s", exc)
    return logger
