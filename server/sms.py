"""Outbound texts through AWS End User Messaging, using the AWS CLI's login session."""

import logging
import os

import boto3

log = logging.getLogger(__name__)

SENDER_ID = os.environ.get("AWS_SENDER_ID", "SCAMCHECK")
REGION = os.environ.get("AWS_REGION", "us-east-1")


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
    except Exception as error:  # boto raises many classes; the text is logged as failed either way
        log.warning("sms to %s failed: %s", to_phone, error)
        return False
