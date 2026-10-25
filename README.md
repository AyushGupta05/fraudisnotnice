# Scam Check

Practice scam texts for grandparents. The reflex it builds: never tap the link.

| Folder   | What it is |
|----------|------------|
| `server` | Flask + SQLite. Sends drills through AWS End User Messaging, serves the reveal page, keeps score. |
| `ios`    | The SwiftUI app the grandchild uses: enrol someone, see immunity per scam type, send a drill now. |

## Run it

```bash
aws login
server/run.sh
```

That opens a public tunnel and prints its address. Open `ios/ScamCheck.xcodeproj`, run on your phone,
and paste the address and the token from `server/.env` into the app's settings.

Texts come from the sender ID `SCAMCHECK`. While the AWS account is in the SMS sandbox, only numbers
verified in AWS End User Messaging receive them.

## The rules

- A drill left untouched for 48 hours is a pass. Tapping its link is a slip, and lands on a one-line reveal.
- The first drill lands within three days of consent. A pass stretches the gap by half, a slip halves it.
  Never longer than two months.
- Each drill targets the weakest scam type, untried ones first.
