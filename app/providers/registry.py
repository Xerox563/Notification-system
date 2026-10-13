from app.config import Settings
from app.providers.base import Provider
from app.providers.email_smtp import SmtpEmailProvider
from app.providers.mock import MockProvider


def build_providers(settings: Settings) -> dict[str, list[Provider]]:
    return {
        "email": [
            SmtpEmailProvider("email_primary", settings.smtp_host, settings.smtp_port, settings.email_sender),
            SmtpEmailProvider(
                "email_backup", settings.smtp_host, settings.smtp_port, settings.email_backup_sender
            ),
        ],
        "sms": [
            MockProvider("sms_primary", "sms", settings.sms_failure_rate),
            MockProvider("sms_backup", "sms", settings.backup_failure_rate),
        ],
        "push": [
            MockProvider("push_primary", "push", settings.push_failure_rate),
            MockProvider("push_backup", "push", settings.backup_failure_rate),
        ],
    }
