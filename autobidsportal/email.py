"""Utilities to handle email."""
from __future__ import annotations

from collections.abc import Collection
from smtplib import SMTPAuthenticationError

from flask import current_app
from flask_mail import Mail, Message

mail = Mail()


def send_email(
    subject: str,
    body: str,
    additional_recipients: Collection[str] | None = None,
):
    """Send an email to the configured recipients.

    Parameters
    ----------
    subject
        Email subject

    body
        Main text (body) of email

    additional_recipients
        Additional addresses to send email to
    """
    if not current_app.config["MAIL_ENABLED"]:
        return
    recipients = list(
        set(current_app.config["MAIL_RECIPIENTS"].split(","))
        | (set(additional_recipients) if additional_recipients else set()),
    )
    try:
        mail.send(
            Message(
                subject=subject,
                body=body,
                sender=current_app.config["MAIL_SENDER"],
                recipients=recipients,
            ),
        )
    except SMTPAuthenticationError as err:
        current_app.logger.error(err)
