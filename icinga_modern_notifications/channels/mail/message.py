"""MIME message construction.

Messages are ``multipart/alternative`` with a mandatory ``text/plain`` part
followed by the ``text/html`` part, built with the standard :mod:`email`
package so that Unicode headers and bodies are encoded correctly.
"""

from __future__ import annotations

from email.message import EmailMessage
from email.policy import default
from email.utils import formatdate, make_msgid, parseaddr

from ... import PROJECT_NAME, __version__
from .config import MailSettings
from .renderer import RenderedMail


def build_message(mail: RenderedMail, settings: MailSettings) -> EmailMessage:
    """Build the complete MIME message for ``mail``."""
    message = EmailMessage(policy=default)
    message["Subject"] = mail.subject
    message["From"] = settings.sender
    message["To"] = ", ".join(settings.recipients)
    message["Date"] = formatdate(localtime=True)
    domain = parseaddr(settings.sender)[1].rpartition("@")[2] or None
    message["Message-ID"] = make_msgid(domain=domain)
    message["Auto-Submitted"] = "auto-generated"
    message["X-Mailer"] = f"{PROJECT_NAME} {__version__}"

    message.set_content(mail.text, subtype="plain", charset="utf-8")
    message.add_alternative(mail.html, subtype="html", charset="utf-8")
    return message


def message_bytes(message: EmailMessage) -> bytes:
    """Serialise ``message`` as RFC 5322 bytes suitable for sendmail or ``.eml`` files."""
    return message.as_bytes(policy=default)
