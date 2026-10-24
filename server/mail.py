"""Email alerts through a Gmail account with an app password. Does nothing until configured."""

import logging
import os
import smtplib
from email.message import EmailMessage

log = logging.getLogger(__name__)


def send(subject, text):
    """Email the family. Returns False if email is not set up or fails; the SMS alert still goes out."""
    user = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    recipients = os.environ.get("FAMILY_EMAILS")
    if not (user and password and recipients):
        return False

    message = EmailMessage()
    message["From"] = user
    message["To"] = recipients
    message["Subject"] = subject
    message.set_content(text)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(user, password)
            smtp.send_message(message)
        return True
    except (smtplib.SMTPException, OSError) as error:
        log.warning("email alert failed: %s", error)
        return False
