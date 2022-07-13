"""Utilities to handle email."""

from smtplib import SMTPAuthenticationError

from flask import current_app
from flask_mail import Mail, Message

mail = Mail()


def send_email(subject, body, recipients=None):
    """Send an email to the configured recipients"""
    if not current_app.config["MAIL_ENABLED"]:
        return
    if recipients is None:
        recipients = current_app.config["MAIL_RECIPIENTS"].split(",")
    try:
        mail.send(
            Message(
                subject=subject,
                body=body,
                sender=current_app.config["MAIL_SENDER"],
                recipients=recipients,
            )
        )
    except SMTPAuthenticationError as err:
        current_app.logger.error(err)
