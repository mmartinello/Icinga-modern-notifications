"""Mail notification channel."""

from __future__ import annotations

import argparse

from ..base import Channel


class MailChannel(Channel):
    """Deliver notifications as multipart plain-text/HTML email."""

    name = "mail"
    help = "send notifications by email"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add mail-specific options (none yet)."""

    def run(self, args: argparse.Namespace) -> None:
        """Build and deliver the email (not implemented yet)."""
