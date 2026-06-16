"""Async SMTP adapter for backup-failure alerts and quarterly access reports."""

from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result


class SmtpAdapter:
    def __init__(self, *, host: str, port: int = 25, use_tls: bool = False) -> None:
        self._host = host
        self._port = port
        self._use_tls = use_tls

    async def send(
        self, *, sender: str, recipients: list[str], subject: str, body: str
    ) -> Result[None, DomainError]:
        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg.set_content(body)
        try:
            await aiosmtplib.send(
                msg, hostname=self._host, port=self._port, use_tls=self._use_tls
            )
            return Ok(None)
        except aiosmtplib.SMTPException:
            return Err(DomainError.EXTERNAL_UNAVAILABLE)
