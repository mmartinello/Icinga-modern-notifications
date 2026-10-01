#!/usr/bin/env python3
"""Render sample notifications for every status to static HTML files.

Usage (from anywhere)::

    python3 examples/render_examples.py [OUTPUT_DIR]

The default output directory is ``examples/emails``. Besides one HTML file per
scenario, an ``index.html`` gallery linking all of them is generated. The
samples use the real templates and rendering pipeline, so they always reflect
the current look of the emails.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from icinga_modern_notifications.channels.mail.renderer import MailRenderer  # noqa: E402
from icinga_modern_notifications.channels.mail.subject import build_subject  # noqa: E402
from icinga_modern_notifications.icingaweb import object_url  # noqa: E402
from icinga_modern_notifications.model import Notification, ObjectKind, Tag  # noqa: E402

TIMESTAMP = 1790603551  # 28/09/2026 15:52:31 Europe/Rome
ICINGAWEB = "https://monitoring.example.com/icingaweb2"
LOCATION = Tag("Location", "DC Milano")

SERVICE = dict(
    kind=ObjectKind.SERVICE,
    host="postgres01",
    host_display_name="PostgreSQL primary",
    address="10.0.10.21",
    service="postgres",
    service_display_name="PostgreSQL",
    environment="PROD",
    timestamp=TIMESTAMP,
    icingaweb_url=ICINGAWEB,
)

HOST = dict(
    kind=ObjectKind.HOST,
    host="postgres01",
    host_display_name="PostgreSQL primary",
    address="10.0.10.21",
    address6="2001:db8:10::21",
    environment="PROD",
    timestamp=TIMESTAMP,
    icingaweb_url=ICINGAWEB,
)

#: name -> (description, notification)
SCENARIOS: dict[str, tuple[str, Notification]] = {
    "service-critical": (
        "Service CRITICAL with notes and long output",
        Notification(
            **SERVICE,
            notification_type="Problem",
            state="CRITICAL",
            output="CRITICAL - PostgreSQL is not accepting connections on port 5432",
            long_output="connection to server at \"10.0.10.21\", port 5432 failed: "
            "Connection refused\nIs the server running on that host and accepting "
            "TCP/IP connections?",
            notes="Main PostgreSQL database for the ERP.\nOn-call DBA: +39 000 0000000",
            duration=974,
            tags=(LOCATION, Tag("Team", "DBA")),
        ),
    ),
    "service-warning": (
        "Service WARNING",
        Notification(
            **{**SERVICE, "service": "disk-var", "service_display_name": "Disk /var"},
            notification_type="Problem",
            state="WARNING",
            output="DISK WARNING - free space: /var 4096 MB (8.2% inode=91%)",
            duration=2710,
        ),
    ),
    "service-unknown": (
        "Service UNKNOWN",
        Notification(
            **{**SERVICE, "service": "backup", "service_display_name": "Nightly backup"},
            notification_type="Problem",
            state="UNKNOWN",
            output="UNKNOWN - cannot read backup status file /var/lib/backup/status.json",
            duration=312,
        ),
    ),
    "service-recovery": (
        "Service RECOVERY",
        Notification(
            **SERVICE,
            notification_type="Recovery",
            state="OK",
            output="OK - PostgreSQL is accepting connections (12 ms)",
            duration=47,
        ),
    ),
    "service-acknowledgement": (
        "Service acknowledgement with author and comment",
        Notification(
            **SERVICE,
            notification_type="Acknowledgement",
            state="CRITICAL",
            output="CRITICAL - PostgreSQL is not accepting connections on port 5432",
            author="mattia",
            comment="Investigating, the database is being restarted.",
            duration=1260,
        ),
    ),
    "host-down": (
        "Host DOWN",
        Notification(
            **HOST,
            notification_type="Problem",
            state="DOWN",
            output="PING CRITICAL - Packet loss = 100%",
            notes="Physical server in rack B4.",
            duration=187200,
            tags=(LOCATION,),
        ),
    ),
    "host-recovery": (
        "Host RECOVERY",
        Notification(
            **HOST,
            notification_type="Recovery",
            state="UP",
            output="PING OK - Packet loss = 0%, RTA = 0.42 ms",
            duration=12420,
            tags=(LOCATION,),
        ),
    ),
    "service-warning-many-tags": (
        "Service WARNING with many tags",
        Notification(
            **{**SERVICE, "service": "erp-api", "service_display_name": "ERP API latency"},
            notification_type="Problem",
            state="WARNING",
            output="HTTP WARNING - response time 2.8 s (warning at 2 s)",
            duration=640,
            tags=(
                LOCATION,
                Tag("Team", "Applications"),
                Tag("Customer", "ACME S.p.A."),
                Tag("Service level", "Gold 24x7"),
                Tag("Cluster", "erp-prod-a"),
                Tag("Owner", "m.rossi"),
            ),
        ),
    ),
    "service-critical-minimal": (
        "Service CRITICAL without any optional data",
        Notification(
            kind=ObjectKind.SERVICE,
            notification_type="Problem",
            state="CRITICAL",
            host="web01",
            service="http",
            output="HTTP CRITICAL - Connection timed out after 10 seconds",
            timestamp=TIMESTAMP,
        ),
    ),
}


def render_all(output_dir: Path) -> list[Path]:
    """Render every scenario and the gallery; return the written HTML files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    renderer = MailRenderer(REPO)
    written = []
    items = []
    for name, (description, notification) in SCENARIOS.items():
        subject = build_subject(notification)
        mail = renderer.render(notification, subject, object_url(notification))
        path = output_dir / f"{name}.html"
        path.write_text(mail.html, encoding="utf-8")
        written.append(path)
        items.append(
            f'<li><a href="{name}.html">{html.escape(description)}</a>'
            f"<br><code>{html.escape(subject)}</code></li>"
        )

    index = output_dir / "index.html"
    index.write_text(
        "<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>Icinga Modern Notifications - examples</title></head>"
        "<body style=\"font-family:sans-serif; max-width:720px; margin:24px auto; "
        "padding:0 16px; line-height:1.5;\">"
        "<h1>Icinga Modern Notifications - email examples</h1>"
        "<ul>" + "".join(items) + "</ul></body></html>\n",
        encoding="utf-8",
    )
    return written


def main() -> int:
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "examples" / "emails"
    for path in render_all(output_dir):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
