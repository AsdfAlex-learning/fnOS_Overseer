import os
import smtplib
import ssl
from typing import List, Optional, Tuple, Dict
from email.mime.text import MIMEText
from email.utils import formataddr
from .base_notify import BaseNotify


class EmailNotify(BaseNotify):
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "0") or "0")
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASS", "")
        self.smtp_tls = os.getenv("SMTP_TLS", "true").lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        self.email_from = os.getenv("EMAIL_FROM", self.smtp_user or "")
        self.email_to_env = os.getenv("EMAIL_TO", "")

    def validate_config(self) -> Tuple[bool, List[str]]:
        missing = []
        if not self.smtp_host:
            missing.append("SMTP_HOST")
        if not self.smtp_port:
            missing.append("SMTP_PORT")
        if not self.smtp_user:
            missing.append("SMTP_USER")
        if not self.smtp_pass:
            missing.append("SMTP_PASS")
        if not self.email_from:
            missing.append("EMAIL_FROM")
        if not self.email_to_env:
            missing.append("EMAIL_TO")
        return (len(missing) == 0, missing)

    def _parse_recipients(self, to: Optional[List[str]]) -> List[str]:
        if to and len(to) > 0:
            return to
        if not self.email_to_env:
            return []
        return [x.strip() for x in self.email_to_env.split(",") if x.strip()]

    def send(self, subject: str, content: str, to: Optional[List[str]] = None) -> bool:
        ok, missing = self.validate_config()
        if not ok:
            return False
        recipients = self._parse_recipients(to)
        if not recipients:
            return False
        msg = MIMEText(content, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = formataddr(("fnOS Overseer", self.email_from))
        msg["To"] = ", ".join(recipients)
        try:
            if self.smtp_tls and self.smtp_port == 465:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    self.smtp_host, self.smtp_port, context=context
                ) as server:
                    server.login(self.smtp_user, self.smtp_pass)
                    server.sendmail(self.email_from, recipients, msg.as_string())
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.ehlo()
                    if self.smtp_tls:
                        server.starttls(context=ssl.create_default_context())
                        server.ehlo()
                    server.login(self.smtp_user, self.smtp_pass)
                    server.sendmail(self.email_from, recipients, msg.as_string())
            return True
        except Exception:
            return False
