"""Mail channel configuration (sender and recipients)."""

from __future__ import annotations

from dataclasses import dataclass
from email.utils import formataddr, parseaddr

from ...errors import ValidationError


def normalize_address(value: str, what: str) -> str:
    """Validate a single mailbox (``addr`` or ``Name <addr>``) and normalise it."""
    text = value.strip()
    if not text:
        raise ValidationError(f"{what} address cannot be empty")
    if any(char in text for char in "\r\n"):
        raise ValidationError(f"invalid {what} address {value!r}")
    name, addr = parseaddr(text)
    if not addr or "@" not in addr or addr.startswith("@") or addr.endswith("@"):
        raise ValidationError(f"invalid {what} address {value!r}")
    return formataddr((name, addr)) if name else addr


@dataclass(frozen=True)
class MailSettings:
    """Mail-specific settings that do not belong to the notification model."""

    sender: str
    recipients: tuple[str, ...]

    @classmethod
    def create(cls, sender: str, recipients: list[str]) -> MailSettings:
        """Validate and normalise sender and recipients."""
        if not recipients:
            raise ValidationError("at least one recipient (--to) is required")
        return cls(
            sender=normalize_address(sender, "sender"),
            recipients=tuple(normalize_address(r, "recipient") for r in recipients),
        )
