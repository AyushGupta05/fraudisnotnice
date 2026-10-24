# Scam Check

Practice scam texts for grandparents, so the reflex they build is "forward anything odd to the family".

Three parts, no paid services:

| Folder   | What it is |
|----------|------------|
| `server` | Flask + SQLite. Decides when drills go out, scores forwards and clicks, serves the reveal page, alerts the family. |
| `phone`  | Two iPhone Shortcuts. Your own phone sends the texts and posts replies back; the server never touches SMS. |
| `ios`    | The SwiftUI app the grandchild uses: enrol someone, see immunity per scam type, send a drill now. |

## Run it

```bash
server/run.sh
```

That opens a public tunnel, prints its address, and rebuilds the two shortcuts for it. Then:

1. AirDrop `phone/*.shortcut` to your iPhone and add them.
2. In Shortcuts on the phone, add Time of Day automations that run **Scam Check Pump**
   (a few across the day, Run Immediately), and a Message automation for each enrolled person
   that runs **Scam Check Inbound**.
3. Open `ios/ScamCheck.xcodeproj`, pick your team under Signing, run on your phone.
4. In the app's settings, paste the tunnel address and the token from `server/.env`.

Email alerts are optional: fill the Gmail lines in `server/.env` with an app password.

## The rules

- First drill lands within three days of consent. Forwarding stretches the gap by half, clicking halves it,
  silence for 48 hours shrinks it a little. Never longer than two months.
- Each drill targets the weakest scam type, untried ones first.
- Forwarding a text that is not a drill alerts every family number: it is probably real.
