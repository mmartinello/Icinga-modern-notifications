"""Exit codes and exception hierarchy.

Every exception raised deliberately by the application derives from
:class:`NotificationError` and carries the process exit code that must be
returned when it reaches the command-line entry point.
"""

from enum import IntEnum


class ExitCode(IntEnum):
    """Deterministic process exit codes."""

    SUCCESS = 0
    RUNTIME_ERROR = 1
    USAGE_ERROR = 2
    TEMPLATE_ERROR = 3
    DELIVERY_ERROR = 4


class NotificationError(Exception):
    """Base class for all expected application errors."""

    exit_code: ExitCode = ExitCode.RUNTIME_ERROR


class ValidationError(NotificationError):
    """Invalid command-line arguments or notification data."""

    exit_code = ExitCode.USAGE_ERROR


class TemplateError(NotificationError):
    """A template is missing, unreadable or cannot be rendered."""

    exit_code = ExitCode.TEMPLATE_ERROR


class DeliveryError(NotificationError):
    """The notification could not be handed over to the delivery channel."""

    exit_code = ExitCode.DELIVERY_ERROR
