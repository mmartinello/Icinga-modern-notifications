# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
