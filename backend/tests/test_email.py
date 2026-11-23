from app.core.database import settings
from app.services.email_templates import verification_email_template
from app.services.email import build_verification_url
from app.services.email import send_verification_email
from app.services.email import build_password_reset_url
from app.services.email import send_password_reset_email
from app.services.email import (
    send_email,
    EmailDeliveryError,
)


def test_send_email_successfully(monkeypatch):
    captured_payload = {}

    def mock_send(payload):
        captured_payload.update(payload)
        return {"id": "test-email-id"}

    monkeypatch.setattr(
        settings,
        "RESEND_API_KEY",
        "test-resend-api-key",
    )

    monkeypatch.setattr(
        "app.services.email.resend.Emails.send",
        mock_send,
    )

    send_email(
        recipient="user@example.com",
        subject="Verify your email",
        html_content="<h1>Welcome</h1>",
    )

    assert captured_payload["to"] == ["user@example.com"]
    assert captured_payload["subject"] == "Verify your email"
    assert captured_payload["html"] == "<h1>Welcome</h1>"
    assert captured_payload["from"] == settings.EMAIL_FROM


def test_send_email_fails_without_api_key(monkeypatch):
    monkeypatch.setattr(
        settings,
        "RESEND_API_KEY",
        None,
    )

    try:
        send_email(
            recipient="user@example.com",
            subject="Verify your email",
            html_content="<h1>Welcome</h1>",
        )
        assert False, "Expected EmailDeliveryError"
    except EmailDeliveryError as exc:
        assert str(exc) == "Email delivery is not configured."


def test_send_email_wraps_provider_errors(monkeypatch):
    def mock_send(payload):
        raise RuntimeError("Simulated provider failure")

    monkeypatch.setattr(
        settings,
        "RESEND_API_KEY",
        "test-resend-api-key",
    )

    monkeypatch.setattr(
        "app.services.email.resend.Emails.send",
        mock_send,
    )

    try:
        send_email(
            recipient="user@example.com",
            subject="Verify your email",
            html_content="<h1>Welcome</h1>",
        )
        assert False, "Expected EmailDeliveryError"
    except EmailDeliveryError as exc:
        assert str(exc) == (
            "The email provider could not send the message."
        )
        assert isinstance(exc.__cause__, RuntimeError)

def test_verification_email_template_contains_required_content():
    html = verification_email_template(
        recipient_name="Omoefe",
        verification_url=(
            "http://localhost:5173/verify-email?token=test-token"
        ),
    )

    assert "Welcome to FlexTech CareerOS, Omoefe!" in html
    assert "Verify Email Address" in html
    assert "test-token" in html
    assert "24 hours" in html
    assert "<html>" in html


def test_verification_email_template_escapes_user_input():
    html = verification_email_template(
        recipient_name="<script>alert('test')</script>",
        verification_url="https://example.com/verify?token=test",
    )

    assert "<script>" not in html
    assert "&lt;script&gt;" in html

def test_build_verification_url():
    url = build_verification_url("sample-token-123")

    assert url == (
        "http://localhost:5173/"
        "verify-email?token=sample-token-123"
    )


def test_build_verification_url_handles_trailing_slash(monkeypatch):
    monkeypatch.setattr(
        settings,
        "FRONTEND_URL",
        "http://localhost:5173/",
    )

    url = build_verification_url("sample-token-123")

    assert url == (
        "http://localhost:5173/"
        "verify-email?token=sample-token-123"
    )

def test_send_verification_email(monkeypatch):
    captured = {}

    def mock_send_email(recipient, subject, html_content):
        captured["recipient"] = recipient
        captured["subject"] = subject
        captured["html_content"] = html_content

    monkeypatch.setattr(
        "app.services.email.send_email",
        mock_send_email,
    )

    send_verification_email(
        recipient="user@example.com",
        recipient_name="Omoefe",
        verification_token="test-token-123",
    )

    assert captured["recipient"] == "user@example.com"
    assert captured["subject"] == (
        "Verify your FlexTech CareerOS account"
    )
    assert "Omoefe" in captured["html_content"]
    assert "test-token-123" in captured["html_content"]
    assert "verify-email" in captured["html_content"]

def test_password_reset_email_template_contains_required_content():
    from app.services.email_templates import (
        password_reset_email_template,
    )

    html = password_reset_email_template(
        recipient_name="Omoefe",
        reset_url="http://localhost:5173/reset-password?token=test123",
    )

    assert "Password Reset Request" in html
    assert "Omoefe" in html
    assert "Reset Password" in html
    assert "30 minutes" in html
    assert "token=test123" in html


def test_password_reset_email_template_escapes_user_input():
    from app.services.email_templates import (
        password_reset_email_template,
    )

    html = password_reset_email_template(
        recipient_name="<script>alert('test')</script>",
        reset_url="https://example.com/reset?token=test123&next=home",
    )

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&amp;" in html


def test_build_password_reset_url():
    url = build_password_reset_url("sample-reset-token")

    assert url == (
        "http://localhost:5173/"
        "reset-password?token=sample-reset-token"
    )


def test_send_password_reset_email(monkeypatch):
    captured = {}

    def mock_send_email(recipient, subject, html_content):
        captured["recipient"] = recipient
        captured["subject"] = subject
        captured["html_content"] = html_content

    monkeypatch.setattr(
        "app.services.email.send_email",
        mock_send_email,
    )

    send_password_reset_email(
        recipient="user@example.com",
        recipient_name="Omoefe",
        reset_token="test-reset-token-123",
    )

    assert captured["recipient"] == "user@example.com"
    assert captured["subject"] == (
        "Reset your FlexTech CareerOS password"
    )
    assert "Omoefe" in captured["html_content"]
    assert "test-reset-token-123" in captured["html_content"]
    assert "reset-password" in captured["html_content"]
