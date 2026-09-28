"""Jinja2 rendering of mail notifications.

Presentation lives in administrator-controlled template files located in the
template directory (by default the directory containing the executable):

* ``notification.txt.j2`` - plain-text body (no autoescaping);
* ``notification.html.j2`` - HTML body (autoescaping always enabled).

Templates receive the :class:`~icinga_modern_notifications.model.Notification`
as ``n`` plus a few helper values; externally supplied strings are never
marked as safe HTML.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import jinja2
from markupsafe import Markup, escape

from ... import PROJECT_NAME, __version__
from ...errors import TemplateError
from ...model import Notification
from ...utils import format_duration, format_timestamp

TEXT_TEMPLATE = "notification.txt.j2"
HTML_TEMPLATE = "notification.html.j2"


def nl2br(value: object) -> Markup:
    """Escape ``value`` and turn line breaks into ``<br>`` (HTML templates only)."""
    lines = str(value).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return Markup("<br>\n").join(escape(line) for line in lines)


@dataclass(frozen=True)
class RenderedMail:
    """Rendered subject and bodies of a mail notification."""

    subject: str
    text: str
    html: str


class MailRenderer:
    """Render mail bodies from the templates in ``template_dir``."""

    def __init__(self, template_dir: Path) -> None:
        self.template_dir = Path(template_dir)
        if not self.template_dir.is_dir():
            raise TemplateError(
                f"template directory {str(self.template_dir)!r} does not exist "
                "or is not a directory"
            )
        self._text_env = self._environment(autoescape=False)
        self._html_env = self._environment(autoescape=True)

    def _environment(self, *, autoescape: bool) -> jinja2.Environment:
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_dir)),
            autoescape=autoescape,
            undefined=jinja2.StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
        env.filters["datetime"] = format_timestamp
        env.filters["duration"] = format_duration
        if autoescape:
            env.filters["nl2br"] = nl2br
        return env

    def _render(
        self, env: jinja2.Environment, name: str, context: dict[str, object]
    ) -> str:
        path = self.template_dir / name
        try:
            return env.get_template(name).render(context)
        except jinja2.TemplateNotFound:
            raise TemplateError(f"template {str(path)!r} not found") from None
        except jinja2.TemplateSyntaxError as exc:
            raise TemplateError(
                f"syntax error in template {str(path)!r} line {exc.lineno}: {exc.message}"
            ) from None
        except (jinja2.TemplateError, OSError, UnicodeDecodeError) as exc:
            raise TemplateError(f"cannot render template {str(path)!r}: {exc}") from None

    @staticmethod
    def context(
        notification: Notification, subject: str, icingaweb_link: str | None
    ) -> dict[str, object]:
        """Return the variables available to templates."""
        return {
            "n": notification,
            "subject": subject,
            "icingaweb_link": icingaweb_link,
            "project_name": PROJECT_NAME,
            "version": __version__,
        }

    def render_text(self, context: dict[str, object]) -> str:
        """Render the plain-text body."""
        return self._render(self._text_env, TEXT_TEMPLATE, context)

    def render_html(self, context: dict[str, object]) -> str:
        """Render the HTML body."""
        return self._render(self._html_env, HTML_TEMPLATE, context)

    def render(
        self, notification: Notification, subject: str, icingaweb_link: str | None
    ) -> RenderedMail:
        """Render both bodies; nothing is returned unless both succeed."""
        context = self.context(notification, subject, icingaweb_link)
        return RenderedMail(
            subject=subject,
            text=self.render_text(context),
            html=self.render_html(context),
        )
