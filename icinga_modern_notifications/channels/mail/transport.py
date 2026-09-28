"""Mail delivery through the local sendmail-compatible MTA.

SMTP relaying, TLS, queueing, retries and routing are delegated to the host
MTA (Postfix, Exim, msmtp, ...). The MTA is always executed directly, never
through a shell.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from email.utils import parseaddr
from pathlib import Path

from ...errors import DeliveryError

DEFAULT_SENDMAIL_PATH = Path("/usr/sbin/sendmail")

#: Seconds to wait for the MTA to accept the message.
SENDMAIL_TIMEOUT = 60


class SendmailTransport:
    """Hand complete MIME messages over to a sendmail-compatible executable."""

    def __init__(
        self, sendmail_path: Path = DEFAULT_SENDMAIL_PATH, timeout: float = SENDMAIL_TIMEOUT
    ) -> None:
        self.sendmail_path = Path(sendmail_path)
        self.timeout = timeout

    def command(self, recipients: Sequence[str]) -> list[str]:
        """Return the sendmail argument vector for ``recipients``.

        ``-oi`` stops a line containing a single dot from ending the message;
        ``--`` guarantees recipients are never interpreted as options.
        """
        addresses = [parseaddr(recipient)[1] for recipient in recipients]
        return [str(self.sendmail_path), "-oi", "--", *addresses]

    def send(self, message: bytes, recipients: Sequence[str]) -> None:
        """Deliver ``message`` to ``recipients``.

        :raises DeliveryError: if sendmail is missing, fails or times out.
        """
        if not recipients:
            raise DeliveryError("no recipients to deliver the message to")
        command = self.command(recipients)
        try:
            result = subprocess.run(
                command,
                input=message,
                capture_output=True,
                timeout=self.timeout,
                check=False,
                shell=False,
            )
        except FileNotFoundError:
            raise DeliveryError(
                f"sendmail executable {str(self.sendmail_path)!r} not found "
                "(install an MTA or use --sendmail-path)"
            ) from None
        except PermissionError:
            raise DeliveryError(
                f"sendmail executable {str(self.sendmail_path)!r} is not executable"
            ) from None
        except subprocess.TimeoutExpired:
            raise DeliveryError(
                f"sendmail {str(self.sendmail_path)!r} did not complete within "
                f"{self.timeout:g} seconds"
            ) from None
        except OSError as exc:
            raise DeliveryError(
                f"cannot execute sendmail {str(self.sendmail_path)!r}: {exc}"
            ) from None

        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", "replace").strip()
            if len(detail) > 500:
                detail = detail[:500] + "..."
            message_text = (
                f"sendmail {str(self.sendmail_path)!r} exited with status "
                f"{result.returncode}"
            )
            raise DeliveryError(f"{message_text}: {detail}" if detail else message_text)
