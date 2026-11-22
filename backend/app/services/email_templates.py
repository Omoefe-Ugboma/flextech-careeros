from html import escape


def verification_email_template(
    recipient_name: str,
    verification_url: str,
) -> str:
    safe_name = escape(recipient_name)
    safe_url = escape(verification_url, quote=True)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Verify your email</title>
    </head>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: auto; padding: 30px;">
            <h2>Welcome to FlexTech CareerOS, {safe_name}!</h2>

            <p>
                Thank you for creating your account.
                Please verify your email address to activate
                your account.
            </p>

            <a
                href="{safe_url}"
                style="
                    display: inline-block;
                    padding: 12px 24px;
                    background-color: #2563eb;
                    color: white;
                    text-decoration: none;
                    border-radius: 6px;
                "
            >
                Verify Email Address
            </a>

            <p>
                This verification link expires after 24 hours.
            </p>

            <p>
                If you did not create this account, you can
                safely ignore this email.
            </p>

            <p>FlexTech CareerOS Team</p>
        </div>
    </body>
    </html>
    """