from urllib.parse import urlencode
import resend
from app.core.database import settings

class EmailDeliveryError(Exception):
    """Raised when an email cannot be delivered."""

def build_verification_url(token: str) -> str:
    query = urlencode({"token": token})

    return (
        f"{settings.FRONTEND_URL.rstrip('/')}"
        f"/verify-email?{query}"
    )

def build_password_reset_url(token: str) -> str:
    query = urlencode({"token": token})

    return (
        f"{settings.FRONTEND_URL.rstrip('/')}"
        f"/reset-password?{query}"
    )


def send_password_reset_email(
    recipient: str,
    recipient_name: str,
    reset_token: str,
) -> None:
    from app.services.email_templates import (
        password_reset_email_template,
    )

    reset_url = build_password_reset_url(reset_token)

    html_content = password_reset_email_template(
        recipient_name=recipient_name,
        reset_url=reset_url,
    )

    send_email(
        recipient=recipient,
        subject="Reset your FlexTech CareerOS password",
        html_content=html_content,
    )

def send_verification_email(
    recipient: str,
    recipient_name: str,
    verification_token: str,
) -> None:
    from app.services.email_templates import (
        verification_email_template,
    )

    verification_url = build_verification_url(
        verification_token
    )

    html_content = verification_email_template(
        recipient_name=recipient_name,
        verification_url=verification_url,
    )

    send_email(
        recipient=recipient,
        subject="Verify your FlexTech CareerOS account",
        html_content=html_content,
    )

def send_email(
    recipient: str,
    subject: str,
    html_content: str,
) -> None:
    if not settings.RESEND_API_KEY:
        raise EmailDeliveryError(
            "Email delivery is not configured."
        )

    try:
        resend.api_key = settings.RESEND_API_KEY

        resend.Emails.send(
            {
                "from": settings.EMAIL_FROM,
                "to": [recipient],
                "subject": subject,
                "html": html_content,
            }
        )

    except Exception as exc:
        raise EmailDeliveryError(
            "The email provider could not send the message."
        ) from exc
