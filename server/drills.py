"""Practice scam templates, one set per scam type.

Placeholders:
  {name}        what the family calls the target, e.g. "Nana"
  {nickname}    what the target calls the grandchild, e.g. "Jamie"
  {grandchild}  the grandchild's real name, used on the reveal page
  {bank}        the target's bank
  {parcel_firm} the parcel firm the target uses
  {link}        the unique reveal link for this drill
"""

import random

SCAM_TYPES = {
    "family": "Family impersonation",
    "bank": "Bank",
    "parcel": "Parcel delivery",
    "gov": "HMRC / government",
    "prize": "Prize or giveaway",
}

TEMPLATES = {
    "family": [
        {
            "body": "Hi {name}, it's {nickname}. New number, my old phone broke. Save this one! "
                    "Can't talk right now, I'm in a bit of a mess with a bill. Can you have a look at this for me? {link}",
            "tell": "A 'new number' text asking for help with money. Ring {grandchild} on the number you already have before you believe a new one.",
        },
        {
            "body": "{name} it's {nickname}, texting from a friend's phone, mine's been nicked. "
                    "Need a hand sorting something quickly, details here: {link}",
            "tell": "Urgency plus a new number. Family in real trouble will still answer when you ring the number you already have.",
        },
    ],
    "bank": [
        {
            "body": "{bank}: A payment of £389.00 to CURRYS was attempted from your account. "
                    "If this was NOT you, secure your account now: {link}",
            "tell": "Real banks never text a link to 'secure your account'. Ring the number on the back of your card instead.",
        },
        {
            "body": "{bank} Alert: a new device was added to your online banking. "
                    "If you did not do this, cancel it here within 2 hours: {link}",
            "tell": "A deadline and a link. {bank} will never rush you. Hang up and ring the number on your card.",
        },
    ],
    "parcel": [
        {
            "body": "{parcel_firm}: We tried to deliver your parcel today but nobody was in. "
                    "Reschedule and pay the £1.45 redelivery fee: {link}",
            "tell": "{parcel_firm} does not charge small fees by text. The tiny fee is a trick to get your card details.",
        },
        {
            "body": "{parcel_firm}: your package is held at our depot due to an unpaid customs charge of £2.99. "
                    "Pay to release it: {link}",
            "tell": "Were you even expecting a parcel? Check on the official website or app, never through a link in a text.",
        },
    ],
    "gov": [
        {
            "body": "HMRC: You are owed a tax refund of £246.71. Claim before the deadline: {link}",
            "tell": "HMRC never texts about refunds. It writes letters or uses your online account.",
        },
        {
            "body": "GOV.UK: Your Winter Fuel Payment needs your details confirming or it will be cancelled. Confirm here: {link}",
            "tell": "Government departments do not threaten to cancel payments by text. Look it up on gov.uk yourself.",
        },
    ],
    "prize": [
        {
            "body": "Congratulations {name}! Your number was drawn in the Tesco Clubcard monthly giveaway. "
                    "Claim your £500 voucher: {link}",
            "tell": "You cannot win a draw you never entered. Prize texts with a link are always a scam.",
        },
        {
            "body": "You've been selected for a free Dyson from a survey you completed. Only 3 left, claim: {link}",
            "tell": "'Only 3 left' is pressure. Real prizes never need you to hurry.",
        },
    ],
}


def make_drill(scam_type, target, link):
    """Return (body, tell) for a target row and a reveal link."""
    template = random.choice(TEMPLATES[scam_type])
    fields = {
        "name": target["name"],
        "nickname": target["nickname"],
        "grandchild": target["grandchild"],
        "bank": target["bank"],
        "parcel_firm": target["parcel_firm"],
        "link": link,
    }
    return template["body"].format(**fields), template["tell"].format(**fields)
