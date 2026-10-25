import SwiftUI

struct TargetView: View {
    let targetID: Int
    @Environment(\.dismiss) private var dismiss
    @State private var target: Target?
    @State private var error: String?
    @State private var confirmingForget = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if let target {
                    scoreboard(target)
                    byType(target)
                    recentDrills(target)
                    actions(target)
                }
                if let error {
                    Text(error).foregroundStyle(Retro.ink)
                }
            }
            .padding(16)
        }
        .retroScreen()
        .retroTitle(target?.name ?? "")
        .task { await load() }
        .confirmationDialog("Forget \(target?.name ?? "this person")?", isPresented: $confirmingForget, titleVisibility: .visible) {
            Button("Forget them and delete their drills", role: .destructive) { Task { await forget() } }
        }
    }

    private func scoreboard(_ target: Target) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("IMMUNITY").font(Retro.font(12)).foregroundStyle(Retro.ink)
            Text(Retro.percent(target.immunity)).font(Retro.font(44))
            Text(Retro.meter(target.immunity)).font(Retro.font(18))
            Text("STREAK \(target.streak)   POINTS \(target.points)")
                .font(Retro.font(12))
                .foregroundStyle(Retro.ink)
            if let waiting = target.waitingDrill {
                Text("Drill out \(waiting.sentAt.formatted(.relative(presentation: .named))): \(waiting.label). Untouched = pass.")
                    .font(Retro.font(12))
            } else if let due = target.nextDueAt {
                Text("Next drill \(due.formatted(.relative(presentation: .named)))")
                    .font(Retro.font(12))
            }
        }
        .retroBox()
    }

    private func byType(_ target: Target) -> some View {
        Group {
            Heading(text: "By scam type")
            ForEach((target.byType ?? [:]).sorted { $0.value.label < $1.value.label }, id: \.key) { entry in
                HStack {
                    Text(entry.value.label.uppercased()).font(Retro.font(12))
                    Spacer()
                    Text("\(Retro.meter(entry.value.immunity)) \(Retro.percent(entry.value.immunity))")
                        .font(Retro.font(12))
                }
            }
        }
    }

    private func recentDrills(_ target: Target) -> some View {
        Group {
            Heading(text: "Recent drills")
            if let drills = target.recentDrills, !drills.isEmpty {
                ForEach(drills) { drill in
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            Text(drill.label.uppercased()).font(Retro.font(12))
                            Spacer()
                            Text(drill.status.uppercased())
                                .font(Retro.font(12))
                                .foregroundStyle(drill.status == "passed" ? Retro.glow : Retro.ink)
                        }
                        Text(drill.body)
                            .font(Retro.font(12, weight: .regular))
                            .foregroundStyle(Retro.ink)
                            .lineLimit(3)
                    }
                    .retroBox()
                }
            } else {
                Text("None yet.").foregroundStyle(Retro.ink)
            }
        }
    }

    private func actions(_ target: Target) -> some View {
        Group {
            if target.isActive && target.waitingDrill == nil {
                Button("Send a drill now") { Task { await sendNow() } }
                    .buttonStyle(RetroButtonStyle())
            }
            Button("Forget this person") { confirmingForget = true }
                .buttonStyle(RetroButtonStyle(filled: false))
        }
        .padding(.top, 8)
    }

    private func load() async {
        guard let api = API.configured else { return }
        do {
            target = try await api.target(targetID)
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func sendNow() async {
        guard let api = API.configured else { return }
        do {
            _ = try await api.sendNow(target: targetID)
            await load()
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func forget() async {
        guard let api = API.configured else { return }
        do {
            try await api.forget(target: targetID)
            dismiss()
        } catch {
            self.error = error.localizedDescription
        }
    }
}
