"""Notification channels.

A channel turns the channel-independent notification model into a concrete
message and delivers it. Each channel contributes its own command-line
options through :class:`~icinga_modern_notifications.channels.base.Channel`.
"""

from .base import Channel
from .mail import MailChannel


def available_channels() -> list[Channel]:
    """Return one instance of every channel supported by this version."""
    return [MailChannel()]
