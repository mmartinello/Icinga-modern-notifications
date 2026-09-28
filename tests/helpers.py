"""Shared helpers for the test-suite."""

from __future__ import annotations

import contextlib
import io

from icinga_modern_notifications.cli import main

HOST_ARGS = [
    "mail",
    "host",
    "--notification-type", "Problem",
    "--state", "DOWN",
    "--host", "postgres01",
    "--output", "PING CRITICAL - Packet loss = 100%",
    "--from", "Icinga <icinga@example.com>",
    "--to", "admin@example.com",
    "--timestamp", "1790000000",
]

SERVICE_ARGS = [
    "mail",
    "service",
    "--notification-type", "Problem",
    "--state", "CRITICAL",
    "--host", "postgres01",
    "--service", "PostgreSQL",
    "--output", "CRITICAL - PostgreSQL is not accepting connections",
    "--from", "Icinga <icinga@example.com>",
    "--to", "admin@example.com",
    "--timestamp", "1790000000",
]


def run_cli(*argv: str, **kwargs) -> tuple[int, str, str]:
    """Run the CLI and return (exit code, stdout, stderr)."""
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = main(list(argv), **kwargs)
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
    return code, stdout.getvalue(), stderr.getvalue()
