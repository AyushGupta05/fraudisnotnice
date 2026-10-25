"""Outbound texts through AWS End User Messaging. Does nothing until AWS_SENDER_ID is set."""

import logging
import os

import boto3

log = logging.getLogger(__name__)

SENDER_ID = os.environ.get("AWS_SENDER_ID")
REGION = os.environ.get("AWS_REGION", "us-east-1")


def configured():
    return bool(SENDER_ID)


def send(to_phone, body):
    """Send one text. Returns True on success."""
    try:
        boto3.client("pinpoint-sms-voice-v2", region_name=REGION).send_text_message(
            DestinationPhoneNumber=to_phone,
            OriginationIdentity=SENDER_ID,
            MessageBody=body,
            MessageType="TRANSACTIONAL",
        )
        return True
    except Exception as error:  # boto raises many classes; the outbox keeps the text either way
        log.warning("sms to %s failed: %s", to_phone, error)
        return False
