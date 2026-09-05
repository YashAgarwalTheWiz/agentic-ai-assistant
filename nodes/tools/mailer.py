"""send_email -- write tool. Sends a real email via Gmail SMTP using an
app password. Higher stakes than save_note: once sent, it cannot be
recalled, and there's no local file to check afterward -- the audit log
in memory/approvals.py is the only record of what was actually approved.

Setup (outside this code):
1. Enable 2-Step Verification on the Gmail account that will send mail.
2. Generate an app password at https://myaccount.google.com/apppasswords
3. Add to .env:
     GMAIL_ADDRESS=your_address@gmail.com
     GMAIL_APP_PASSWORD=the16characterpassword (no spaces)
"""

import os
import smtplib
from email.message import EmailMessage

from nodes.tools.registry import tool


def _looks_like_email(address: str) -> bool:
    """A cheap sanity check, not real validation -- just enough to catch
    an obviously wrong argument before handing it to smtplib."""
    return "@" in address and "." in address.split("@")[-1]


@tool(
    name="send_email",
    description=(
        "Send a real email to a specific recipient. Use this ONLY when the "
        "user explicitly asks you to send, email, or write to someone by "
        "email address. Do NOT use it to save information for later, to "
        "answer a question, or on your own initiative -- only when sending "
        "an email is literally what was asked for. This delivers a real "
        "message to a real inbox and cannot be undone once sent, so the "
        "user must approve the exact recipient, subject, and body first."
    ),
    parameters={
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "The recipient's email address, e.g. 'someone@example.com'.",
            },
            "subject": {
                "type": "string",
                "description": "A short, clear subject line.",
            },
            "body": {
                "type": "string",
                "description": (
                    "The full email body, written out properly in plain text "
                    "-- this is what actually gets sent, so do not abbreviate."
                ),
            },
        },
        "required": ["to", "subject", "body"],
    },
    write=True,
)
def send_email(to: str, subject: str, body: str) -> str:
    if not _looks_like_email(to):
        return f"Error: '{to}' doesn't look like a valid email address. Nothing was sent."

    address = os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    if not address or not app_password:
        return (
            "Error: GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be set in .env "
            "before this tool can send anything."
        )

    msg = EmailMessage()
    msg["From"] = address
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(address, app_password)
        server.send_message(msg)

    return f"Email sent to {to}."