from email.message import EmailMessage

import aiosmtplib

from app.providers.base import Message, Provider, ProviderError, SendResult


class SmtpEmailProvider(Provider):
    channel = "email"

    def __init__(self, name: str, host: str, port: int, sender: str):
        self.name = name
        self.host = host
        self.port = port
        self.sender = sender

    async def send(self, message: Message) -> SendResult:
        mail = EmailMessage()
        mail["From"] = self.sender
        mail["To"] = message.recipient
        mail["Subject"] = message.subject
        mail["X-Notification-Id"] = message.notification_id
        mail.set_content(message.body)
        try:
            await aiosmtplib.send(mail, hostname=self.host, port=self.port, timeout=10)
        except (aiosmtplib.SMTPException, OSError) as exc:
            raise ProviderError(f"{self.name} smtp error: {exc}") from exc
        return SendResult(delivered=False)
