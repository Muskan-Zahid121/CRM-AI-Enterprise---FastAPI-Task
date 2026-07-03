import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import partial

from app.config import settings


def _send_email_sync(subject: str, to: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM or settings.SMTP_USER
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(msg["From"], [to], msg.as_string())


async def send_email(subject: str, to: str, html_body: str) -> None:
    loop = asyncio.get_event_loop()
    fn = partial(_send_email_sync, subject, to, html_body)
    await loop.run_in_executor(None, fn)


def format_reset_password_email(app_name: str, otp: str, expires_minutes: int) -> tuple[str, str]:
    subject = f"Reset your password — {app_name}"
    body = f"<p>Your reset code: <strong>{otp}</strong> (expires in {expires_minutes} min)</p>"
    return subject, body
