"""Channel-independent notification model.

The :class:`Notification` class normalises the data received from Icinga 2 and
exposes presentation-neutral derived properties (display status, emoji, ...)
that every channel can consume. It deliberately knows nothing about email,
HTML or any other delivery-specific concept.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import StrEnum

from .errors import ValidationError
from .utils import validate_http_url


class ObjectKind(StrEnum):
    """Kind of Icinga object a notification refers to."""

    HOST = "host"
    SERVICE = "service"


class State(StrEnum):
    """Current state of an Icinga host or service."""

    UP = "UP"
    DOWN = "DOWN"
    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class DisplayStatus(StrEnum):
    """Status shown to humans (headings, subjects, colours...)."""

    UP = "UP"
    DOWN = "DOWN"
    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"
    RECOVERY = "RECOVERY"


#: Valid states for each object kind.
VALID_STATES: dict[ObjectKind, tuple[State, ...]] = {
    ObjectKind.HOST: (State.UP, State.DOWN),
    ObjectKind.SERVICE: (State.OK, State.WARNING, State.CRITICAL, State.UNKNOWN),
}

#: Single source of truth for status emoji. Emoji are a visual enhancement
#: only: the status text is always rendered as well.
STATUS_EMOJI: dict[DisplayStatus, str] = {
    DisplayStatus.CRITICAL: "\N{LARGE RED CIRCLE}",
    DisplayStatus.DOWN: "\N{LARGE RED CIRCLE}",
    DisplayStatus.WARNING: "\N{LARGE ORANGE CIRCLE}",
    DisplayStatus.UNKNOWN: "\N{LARGE PURPLE CIRCLE}",
    DisplayStatus.RECOVERY: "\N{LARGE GREEN CIRCLE}",
    DisplayStatus.OK: "\N{LARGE GREEN CIRCLE}",
    DisplayStatus.UP: "\N{LARGE GREEN CIRCLE}",
}

#: Normalised notification types used by Icinga 2 for problems and recoveries.
PROBLEM_TYPE = "PROBLEM"
RECOVERY_TYPE = "RECOVERY"

#: Human-readable labels for the notification types known to Icinga 2.
#: Unknown types are still accepted and labelled generically.
NOTIFICATION_TYPE_LABELS: dict[str, str] = {
    "PROBLEM": "Problem",
    "RECOVERY": "Recovery",
    "ACKNOWLEDGEMENT": "Acknowledgement",
    "CUSTOM": "Custom notification",
    "FLAPPINGSTART": "Flapping started",
    "FLAPPINGEND": "Flapping ended",
    "DOWNTIMESTART": "Downtime started",
    "DOWNTIMEEND": "Downtime ended",
    "DOWNTIMEREMOVED": "Downtime removed",
}


def normalize_notification_type(value: str) -> str:
    """Normalise an Icinga notification type (``Problem`` -> ``PROBLEM``)."""
    normalized = "".join(value.split()).upper()
    if not normalized:
        raise ValidationError("notification type cannot be empty")
    return normalized


def normalize_state(value: str, kind: ObjectKind) -> State:
    """Normalise and validate a state for the given object kind (case-insensitive)."""
    valid = VALID_STATES[kind]
    text = value.strip().upper()
    for state in valid:
        if state.value == text:
            return state
    choices = ", ".join(state.value for state in valid)
    raise ValidationError(
        f"invalid {kind} state {value!r} (expected one of: {choices})"
    )


def _clean(value: str | None) -> str | None:
    """Turn empty or whitespace-only optional strings into ``None``."""
    if value is None:
        return None
    return value if value.strip() else None


@dataclass(frozen=True, kw_only=True)
class Notification:
    """A normalised Icinga 2 host or service notification.

    Optional attributes are ``None`` when the value is absent or empty, so
    renderers can simply test them for truthiness and omit them entirely.
    """

    kind: ObjectKind
    notification_type: str
    state: State
    host: str
    output: str
    timestamp: float
    host_display_name: str | None = None
    address: str | None = None
    address6: str | None = None
    service: str | None = None
    service_display_name: str | None = None
    long_output: str | None = None
    notes: str | None = None
    environment: str | None = None
    author: str | None = None
    comment: str | None = None
    duration: int | None = None
    icingaweb_url: str | None = None

    def __post_init__(self) -> None:
        kind = ObjectKind(self.kind)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(
            self,
            "notification_type",
            normalize_notification_type(self.notification_type),
        )
        state = self.state
        if not isinstance(state, State) or state not in VALID_STATES[kind]:
            state = normalize_state(str(state), kind)
        object.__setattr__(self, "state", state)

        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, str) and field.name not in ("host", "output"):
                object.__setattr__(self, field.name, _clean(value))
        if self.environment is not None:
            object.__setattr__(self, "environment", self.environment.strip())
        if self.icingaweb_url is not None:
            try:
                url = validate_http_url(self.icingaweb_url)
            except ValueError as exc:
                raise ValidationError(f"Icinga Web: {exc}") from None
            object.__setattr__(self, "icingaweb_url", url)

        if not self.host.strip():
            raise ValidationError("host name cannot be empty")
        if kind is ObjectKind.SERVICE and self.service is None:
            raise ValidationError("service name is required for service notifications")
        if kind is ObjectKind.HOST and (self.service or self.service_display_name):
            raise ValidationError("host notifications cannot refer to a service")
        if self.timestamp < 0:
            raise ValidationError("timestamp cannot be negative")
        if self.duration is not None and self.duration < 0:
            raise ValidationError("duration cannot be negative")

    @property
    def is_service(self) -> bool:
        """Whether this is a service notification."""
        return self.kind is ObjectKind.SERVICE

    @property
    def is_problem(self) -> bool:
        """Whether this is a problem notification."""
        return self.notification_type == PROBLEM_TYPE

    @property
    def is_recovery(self) -> bool:
        """Whether this is a recovery notification."""
        return self.notification_type == RECOVERY_TYPE

    @property
    def notification_type_label(self) -> str:
        """Human-readable notification type (``Downtime started``...)."""
        return NOTIFICATION_TYPE_LABELS.get(
            self.notification_type, self.notification_type.capitalize()
        )

    @property
    def display_status(self) -> DisplayStatus:
        """Status to show in headings and subjects.

        Recovery notifications are displayed as ``RECOVERY`` rather than with
        the plain ``OK``/``UP`` state; everything else uses the current state.
        """
        if self.is_recovery:
            return DisplayStatus.RECOVERY
        return DisplayStatus(self.state.value)

    @property
    def emoji(self) -> str:
        """Emoji associated with :attr:`display_status`."""
        return STATUS_EMOJI[self.display_status]

    @property
    def host_title(self) -> str:
        """Host name for humans: display name if available, else technical name."""
        return self.host_display_name or self.host

    @property
    def service_title(self) -> str | None:
        """Service name for humans: display name if available, else technical name."""
        return self.service_display_name or self.service

    @property
    def object_name(self) -> str:
        """Concise technical identifier (``host`` or ``host / service``)."""
        if self.is_service:
            return f"{self.host} / {self.service}"
        return self.host
