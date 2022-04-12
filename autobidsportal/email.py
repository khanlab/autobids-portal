"""Utilities to handle email."""

from smtplib import SMTPAuthenticationError

from flask import current_app
from flask_mail import Mail, Message

mail = Mail()


def send_email(subject, body):
    """Send an email to the configured recipients"""
    if not current_app.config["MAIL_ENABLED"]:
        return
    try:
        mail.send(
            Message(
                subject=subject,
                body=body,
                sender=current_app.config["MAIL_USERNAME"],
                recipients=current_app.config["MAIL_RECIPIENTS"],
            )
        )
    except SMTPAuthenticationError as err:
        current_app.logger.error(err)
