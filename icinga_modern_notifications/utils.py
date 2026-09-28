"""Formatting and parsing helpers shared by every channel.

Date/time and duration formatting is centralised here so that templates never
contain hardcoded formats. Timestamps are rendered in the local timezone of
the machine running the application (normally the Icinga master/satellite).
"""

from __future__ import annotations

from datetime import datetime

#: Default human-readable date/time format (Italian/European convention).
DATETIME_FORMAT = "%d/%m/%Y %H:%M:%S"

#: Duration units, from the largest to the smallest, with their length in seconds.
_DURATION_UNITS = (
    ("d", 86400),
    ("h", 3600),
    ("m", 60),
    ("s", 1),
)

#: Maximum number of units shown by :func:`format_duration`.
DURATION_PRECISION = 2


def format_timestamp(timestamp: float, fmt: str = DATETIME_FORMAT) -> str:
    """Format a Unix timestamp in the local timezone.

    >>> format_timestamp(0, "%Y")  # doctest: +SKIP
    '1970'
    """
    return datetime.fromtimestamp(timestamp).astimezone().strftime(fmt)


def format_duration(seconds: int, precision: int = DURATION_PRECISION) -> str:
    """Format a duration in seconds as a short human-readable string.

    Only the ``precision`` most significant units are shown, starting from the
    largest non-zero unit; trailing zero units are dropped.

    >>> format_duration(12)
    '12s'
    >>> format_duration(74)
    '1m 14s'
    >>> format_duration(12420)
    '3h 27m'
    >>> format_duration(187200)
    '2d 4h'
    """
    if seconds < 0:
        raise ValueError(f"duration cannot be negative: {seconds}")
    seconds = int(seconds)
    if seconds == 0:
        return "0s"

    parts: list[str] = []
    started = False
    for suffix, length in _DURATION_UNITS:
        value, seconds = divmod(seconds, length)
        if value or started:
            started = True
            if value:
                parts.append(f"{value}{suffix}")
            precision -= 1
            if precision == 0:
                break
    return " ".join(parts)


def parse_non_negative_number(value: str, what: str) -> float:
    """Parse a non-negative decimal number supplied on the command line.

    :raises ValueError: with an administrator-friendly message.
    """
    text = value.strip()
    try:
        number = float(text)
    except ValueError:
        raise ValueError(f"invalid {what}: {value!r} is not a number") from None
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"invalid {what}: {value!r} is not a finite number")
    if number < 0:
        raise ValueError(f"invalid {what}: {value!r} cannot be negative")
    return number


def parse_timestamp(value: str) -> float:
    """Parse a Unix timestamp (seconds since the epoch, fractions allowed)."""
    return parse_non_negative_number(value, "timestamp")


def parse_duration(value: str) -> int:
    """Parse a duration in seconds (fractions are truncated)."""
    return int(parse_non_negative_number(value, "duration"))
