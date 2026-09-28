# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-09-28

First release, providing the mail channel.

### Added

- Project skeleton: launcher script, `icinga_modern_notifications` package,
  channel-oriented command line (`mail host`, `mail service`) and exit codes.
- Centralised date/time and duration formatting helpers.
- Channel-independent notification model with normalised states, display
  status (`RECOVERY` for recoveries) and a centralised status emoji mapping.
- Complete notification options for `mail host` and `mail service`
  (required/optional Icinga data, repeatable `--to`, numeric validation).
- Email subject generation (`🔴 [ICINGA][CRITICAL][PROD] host / service`).
- Icinga Web object links for Icinga DB Web (default) and the legacy
  monitoring module (`--icingaweb-module`), with URL-encoded object names.
- Jinja2 mail renderer with clear template errors and the plain-text
  template `notification.txt.j2`.
- Responsive, table-based HTML template `notification.html.j2` with inline
  CSS, status colours, Outlook-friendly Icinga Web button and escaped content.
- MIME `multipart/alternative` message construction with encoded Unicode
  headers, `Message-ID`, `Date` and `Auto-Submitted`.
- Delivery through the local sendmail-compatible MTA (`--sendmail-path`),
  executed without a shell, and configurable `--template-dir`.
- `--dry-run` and `--dump-html`, `--dump-text`, `--dump-eml` development options.
- Operational logging with `--verbose`, `--debug` and `--syslog`; only
  metadata is logged, never bodies, notes, comments or plugin output.
- Example Icinga 2 `NotificationCommand` definitions and apply rules in
  `examples/icinga2/`.
- Complete README (installation, usage, templates, Icinga integration,
  exit codes, troubleshooting, security).

[Unreleased]: https://github.com/mmartinello/Icinga-modern-notifications/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mmartinello/Icinga-modern-notifications/releases/tag/v0.1.0
