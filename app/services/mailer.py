import smtplib
from email.message import EmailMessage
from ..config import get_settings


def send_email(to: str, subject: str, body: str) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        # No SMTP configured (e.g. local dev) - log instead of failing the request.
        print(f"[mailer] SMTP not configured; would send to {to}: {subject}\n{body}")
        return
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from or settings.smtp_username or "no-reply@team-tracker.local"
    message["To"] = to
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)
