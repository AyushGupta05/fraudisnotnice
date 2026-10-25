import SwiftUI

/// One drill: what was sent, how it ended, or how long until it counts as a pass.
struct DrillRow: View {
    let drill: Drill
    let now: Date

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(drill.label.uppercased()).font(Retro.font(12))
                Spacer()
                Badge(text: badgeText, filled: drill.status == "passed")
            }
            Text(drill.body)
                .font(Retro.font(12, weight: .regular))
                .foregroundStyle(Retro.ink)
                .lineLimit(3)
            if drill.status == "pending", let passesAt = drill.passesAt {
                Bar(fraction: drill.progress(at: now), height: 10)
                Text("Untouched so far. Counts as a pass \(passesAt.formatted(.relative(presentation: .named))).")
                    .font(Retro.font(11))
                    .foregroundStyle(Retro.ink)
            } else if let resolvedAt = drill.resolvedAt {
                Text("\(outcomeText) \(resolvedAt.formatted(.relative(presentation: .named)))")
                    .font(Retro.font(11))
                    .foregroundStyle(Retro.ink)
            }
        }
        .retroBox()
    }

    private var badgeText: String {
        switch drill.status {
        case "passed": "passed"
        case "clicked": "tapped link"
        default: "waiting"
        }
    }

    private var outcomeText: String {
        drill.status == "passed" ? "Left alone, well done." : "Link was tapped and the reveal shown"
    }
}
