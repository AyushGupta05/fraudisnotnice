"""Build the two iPhone shortcuts that do the texting, signed so any iPhone can import them.

    python3 make_shortcuts.py https://your-tunnel.trycloudflare.com

Writes "Scam Check Pump.shortcut" and "Scam Check Inbound.shortcut" next to this file. AirDrop both to the
phone and tap Add Shortcut. Then, in the Shortcuts app on the phone, create the automations that run them:

  * Time of Day: a few across the waking hours (say 9, 12, 15, 18 and 21), each set to Run Immediately
    and running "Scam Check Pump". Shortcuts has no "every hour" trigger, so it is one automation per time.
  * Message: "when I get a message from" each person you enrol, Run Immediately, running
    "Scam Check Inbound". The message is passed in as Shortcut Input.

The server address is baked into both, so rerun this when the tunnel URL changes. run.sh does that for you.
"""

import plistlib
import subprocess
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENV_FILE = HERE.parent / "server" / ".env"
PUMP, INBOUND = "Scam Check Pump", "Scam Check Inbound"


# ---------------------------------------------------------------- the shortcut file format

def action(identifier, **parameters):
    return {"WFWorkflowActionIdentifier": identifier, "WFWorkflowActionParameters": parameters}


def output_of(action_uuid, name):
    """A reference to an earlier action's result."""
    return {"Type": "ActionOutput", "OutputUUID": action_uuid, "OutputName": name}


def shortcut_input(property_name=None):
    """The item the automation handed to the shortcut, optionally one property of it (e.g. a message's Sender)."""
    reference = {"Type": "ExtensionInput"}
    if property_name:
        reference["Aggrandizements"] = [{"Type": "WFPropertyVariableAggrandizement", "PropertyName": property_name}]
    return reference


def variable(reference):
    return {"Value": reference, "WFSerializationType": "WFTextTokenAttachment"}


def text(string="", reference=None):
    """A text field, either plain or consisting of a single inserted variable."""
    attachments = {"{0, 1}": reference} if reference else {}
    return {
        "Value": {"string": "￼" if reference else string, "attachmentsByRange": attachments},
        "WFSerializationType": "WFTextTokenString",
    }


def dictionary(items):
    """A dictionary field, e.g. HTTP headers or a JSON body. Values are text() tokens."""
    return {
        "Value": {"WFDictionaryFieldValueItems": [
            {"WFItemType": 0, "WFKey": text(key), "WFValue": value} for key, value in items
        ]},
        "WFSerializationType": "WFDictionaryFieldValue",
    }


def uid():
    return str(uuid.uuid4()).upper()


def workflow(actions, takes_input):
    return {
        "WFWorkflowClientVersion": "2607.1.3",
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowIcon": {"WFWorkflowIconStartColor": 431817727, "WFWorkflowIconGlyphNumber": 59511},
        "WFWorkflowImportQuestions": [],
        "WFWorkflowTypes": [],
        "WFWorkflowHasShortcutInputVariables": takes_input,
        "WFWorkflowInputContentItemClasses": ["WFStringContentItem", "WFPhoneNumberContentItem"] if takes_input else [],
        "WFWorkflowActions": actions,
    }


# ---------------------------------------------------------------- the two shortcuts

def pump(base_url, token):
    """Ask the server for queued texts, up to five at a time, and send each one."""
    loop, branch, fetch, to, body = uid(), uid(), uid(), uid(), uid()
    contents = output_of(fetch, "Contents of URL")
    return [
        action("is.workflow.actions.repeat.count", WFRepeatCount=5, GroupingIdentifier=loop, WFControlFlowMode=0),
        action("is.workflow.actions.downloadurl", UUID=fetch, WFURL=f"{base_url}/outbox/next", WFHTTPMethod="GET",
               ShowHeaders=True, WFHTTPHeaders=dictionary([("X-Token", text(token))])),
        action("is.workflow.actions.getvalueforkey", UUID=to, WFGetDictionaryValueType="Value",
               WFDictionaryKey="to", WFInput=variable(contents)),
        action("is.workflow.actions.getvalueforkey", UUID=body, WFGetDictionaryValueType="Value",
               WFDictionaryKey="body", WFInput=variable(contents)),
        # If "body" has any value, send it; otherwise the queue is empty, so stop.
        action("is.workflow.actions.conditional", GroupingIdentifier=branch, WFControlFlowMode=0, WFCondition=100,
               WFInput={"Type": "Variable", "Variable": variable(output_of(body, "Dictionary Value"))}),
        action("is.workflow.actions.sendmessage", IntentAppIdentifier="com.apple.MobileSMS", ShowWhenRun=False,
               WFSendMessageContent=text(reference=output_of(body, "Dictionary Value")),
               WFSendMessageActionRecipients=variable(output_of(to, "Dictionary Value"))),
        action("is.workflow.actions.conditional", GroupingIdentifier=branch, WFControlFlowMode=1),
        action("is.workflow.actions.exit"),
        action("is.workflow.actions.conditional", GroupingIdentifier=branch, WFControlFlowMode=2),
        action("is.workflow.actions.repeat.count", GroupingIdentifier=loop, WFControlFlowMode=2),
    ]


def inbound(base_url, token):
    """Post a received message to the server. The server replies by text itself through AWS."""
    return [
        action("is.workflow.actions.downloadurl", UUID=uid(), WFURL=f"{base_url}/inbound", WFHTTPMethod="POST",
               ShowHeaders=True, WFHTTPHeaders=dictionary([("X-Token", text(token))]),
               WFHTTPBodyType="JSON", WFJSONValues=dictionary([
                   ("from", text(reference=shortcut_input("Sender"))),
                   ("body", text(reference=shortcut_input())),
               ])),
    ]


# ---------------------------------------------------------------- writing and signing

def token_from_env():
    for line in ENV_FILE.read_text().splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "SCAMCHECK_TOKEN":
            return value.strip()
    sys.exit(f"SCAMCHECK_TOKEN not found in {ENV_FILE}")


def write_signed(name, actions, takes_input):
    unsigned = HERE / f"{name}.unsigned.shortcut"
    signed = HERE / f"{name}.shortcut"
    with unsigned.open("wb") as handle:
        plistlib.dump(workflow(actions, takes_input), handle)
    try:
        sign(unsigned, signed)
    finally:
        unsigned.unlink(missing_ok=True)
    return signed


def sign(unsigned, signed):
    """Sign with the system tool. It occasionally fails for no reason while Shortcuts.app is busy, so try twice."""
    command = ["shortcuts", "sign", "--mode", "anyone", "--input", str(unsigned), "--output", str(signed)]
    for attempt in (1, 2):
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            return
        time.sleep(1)
    sys.exit(f"shortcuts sign failed: {result.stderr.strip() or result.stdout.strip()}")


def main():
    if len(sys.argv) != 2 or not sys.argv[1].startswith("http"):
        sys.exit(__doc__)
    base_url = sys.argv[1].rstrip("/")
    token = token_from_env()
    for name, actions, takes_input in ((PUMP, pump(base_url, token), False), (INBOUND, inbound(base_url, token), True)):
        print("wrote", write_signed(name, actions, takes_input).name)


if __name__ == "__main__":
    main()
