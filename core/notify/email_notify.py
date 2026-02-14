import os
import smtplib
import ssl
import logging
from typing import List, Optional, Tuple, Dict
from email.mime.text import MIMEText
from email.utils import formataddr
from .base_notify import BaseNotify

logger = logging.getLogger(__name__)


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
        # Validate configuration first
        ok, missing = self.validate_config()
        if not ok:
            logger.error(f"Email configuration incomplete. Missing: {', '.join(missing)}")
            return False

        recipients = self._parse_recipients(to)
        if not recipients:
            logger.error("No valid recipients found")
            return False

        msg = MIMEText(content, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = formataddr(("fnOS Overseer", self.email_from))
        msg["To"] = ", ".join(recipients)

        try:
            if self.smtp_tls and self.smtp_port == 465:
                # Use SMTP_SSL for port 465 (implicit SSL)
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    self.smtp_host, self.smtp_port, context=context, timeout=30
                ) as server:
                    logger.debug(f"Connecting to SMTP server {self.smtp_host}:{self.smtp_port} (SSL)")
                    server.login(self.smtp_user, self.smtp_pass)
                    server.sendmail(self.email_from, recipients, msg.as_string())
                    logger.info(f"Email sent successfully to {recipients}")
            else:
                # Use regular SMTP with optional STARTTLS
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                    logger.debug(f"Connecting to SMTP server {self.smtp_host}:{self.smtp_port}")
                    server.ehlo()
                    if self.smtp_tls:
                        server.starttls(context=ssl.create_default_context())
                        server.ehlo()
                    server.login(self.smtp_user, self.smtp_pass)
                    server.sendmail(self.email_from, recipients, msg.as_string())
                    logger.info(f"Email sent successfully to {recipients}")
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
        except smtplib.SMTPConnectError as e:
            logger.error(f"Failed to connect to SMTP server {self.smtp_host}:{self.smtp_port}: {e}")
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error occurred: {e}")
        except ConnectionRefusedError as e:
            logger.error(f"Connection refused by SMTP server: {e}")
        except TimeoutError as e:
            logger.error(f"SMTP connection timed out: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}", exc_info=True)
        return False
