"""Email subject construction.

The subject is built by the application (Icinga does not provide it) and is
kept independent from template rendering so it can be tested in isolation::

    🔴 [ICINGA][CRITICAL][PROD] postgres01 / PostgreSQL
"""

from __future__ import annotations

from ...model import Notification

SUBJECT_PREFIX = "ICINGA"


def build_subject(notification: Notification) -> str:
    """Return the email subject for ``notification``.

    Technical host/service names are used to keep the subject concise and
    unambiguous; the environment tag is added only when one was supplied.
    """
    tags = [SUBJECT_PREFIX, notification.display_status.value]
    if notification.environment:
        tags.append(notification.environment)
    tag_text = "".join(f"[{tag}]" for tag in tags)
    subject = f"{notification.emoji} {tag_text} {notification.object_name}"
    # Headers must never contain line breaks, whatever Icinga sends us.
    return " ".join(subject.split())
