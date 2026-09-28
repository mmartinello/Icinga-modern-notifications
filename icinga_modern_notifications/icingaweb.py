"""Icinga Web link generation.

All knowledge about Icinga Web routes lives in this module so that templates
only ever receive a ready-to-use, correctly encoded URL.

Two Icinga Web modules are supported:

``icingadb``
    Icinga DB Web (default for current Icinga Web installations):
    ``/icingadb/host?name=HOST`` and ``/icingadb/service?name=SERVICE&host.name=HOST``.

``monitoring``
    The legacy monitoring module (IDO):
    ``/monitoring/host/show?host=HOST`` and
    ``/monitoring/service/show?host=HOST&service=SERVICE``.
"""

from __future__ import annotations

from urllib.parse import quote, urlencode

from .errors import ValidationError
from .model import Notification

#: Route templates: module -> kind -> (path, query parameter names).
ROUTES: dict[str, dict[str, tuple[str, dict[str, str]]]] = {
    "icingadb": {
        "host": ("icingadb/host", {"name": "host"}),
        "service": ("icingadb/service", {"name": "service", "host.name": "host"}),
    },
    "monitoring": {
        "host": ("monitoring/host/show", {"host": "host"}),
        "service": ("monitoring/service/show", {"host": "host", "service": "service"}),
    },
}

DEFAULT_MODULE = "icingadb"


def object_url(notification: Notification, module: str = DEFAULT_MODULE) -> str | None:
    """Return the Icinga Web URL of the notified host/service, or ``None``.

    ``None`` is returned when no Icinga Web base URL was supplied, so that
    renderers can omit the link entirely.
    """
    if not notification.icingaweb_url:
        return None
    try:
        path, params = ROUTES[module][notification.kind.value]
    except KeyError:
        raise ValidationError(f"unsupported Icinga Web module {module!r}") from None
    values = {"host": notification.host, "service": notification.service}
    query = urlencode(
        {name: values[source] for name, source in params.items()}, quote_via=quote
    )
    return f"{notification.icingaweb_url}/{path}?{query}"
