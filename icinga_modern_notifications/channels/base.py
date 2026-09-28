"""Base interface shared by every notification channel."""

from __future__ import annotations

import argparse
from abc import ABC, abstractmethod


class Channel(ABC):
    """A delivery channel such as mail (or, in the future, Teams/webhooks)."""

    #: Sub-command name used on the command line (``icinga-modern-notifications <name> ...``).
    name: str
    #: Short description shown in ``--help``.
    help: str

    @abstractmethod
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add channel-specific options to a host/service sub-command parser."""

    @abstractmethod
    def run(self, args: argparse.Namespace) -> None:
        """Build and deliver the notification described by ``args``."""
