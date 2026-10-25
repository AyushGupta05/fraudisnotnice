import SwiftUI

struct TargetView: View {
    let targetID: Int
    @Environment(\.dismiss) private var dismiss
    @State private var target: Target?
    @State private var error: String?
    @State private var busy = false
    @State private var confirmingForget = false
    @State private var now = Date()
    private let clock = Timer.publish(every: 30, on: .main, in: .common).autoconnect()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if let target {
                    scoreboard(target)
                    if target.status == "pending" { awaitingCode(target) }
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
        .refreshable { await load() }
        .task { await load() }
        .onReceive(clock) { now = $0 }
        .confirmationDialog("Forget \(target?.name ?? "this person")?", isPresented: $confirmingForget, titleVisibility: .visible) {
            Button("Forget them and delete their drills", role: .destructive) { Task { await forget() } }
        }
    }

    private func scoreboard(_ target: Target) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("IMMUNITY  ·  drills left alone").font(Retro.font(12)).foregroundStyle(Retro.ink)
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text(Retro.percent(target.immunity)).font(Retro.font(44))
                Spacer()
                Text("STREAK \(target.streak)\nPOINTS \(target.points)")
                    .font(Retro.font(12))
                    .foregroundStyle(Retro.ink)
                    .multilineTextAlignment(.trailing)
            }
            Bar(fraction: target.immunity.map { Double($0) / 100 }, height: 18)
            if target.waitingDrill != nil {
                Text("A drill is out. Nothing to do but wait.").font(Retro.font(12))
            } else if let due = target.nextDueAt {
                Text("Next drill \(due.formatted(.relative(presentation: .named))), between their waking hours.")
                    .font(Retro.font(12))
            }
        }
        .retroBox()
    }

    private func awaitingCode(_ target: Target) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("They have not read the code back yet. Nothing is sent until they do.")
            Button(busy ? "Sending" : "Text the code again") { Task { await resend() } }
                .buttonStyle(RetroButtonStyle(filled: false))
                .disabled(busy)
        }
        .retroBox()
    }

    private func byType(_ target: Target) -> some View {
        Group {
            Heading(text: "By scam type")
            ForEach((target.byType ?? [:]).sorted { $0.value.label < $1.value.label }, id: \.key) { entry in
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text(entry.value.label.uppercased()).font(Retro.font(12))
                        Spacer()
                        Text(entry.value.attempts == 0 ? "not tried" : "\(entry.value.passed) of \(entry.value.attempts) left alone")
                            .font(Retro.font(11))
                            .foregroundStyle(Retro.ink)
                    }
                    Bar(fraction: entry.value.immunity.map { Double($0) / 100 }, height: 8)
                }
            }
        }
    }

    private func recentDrills(_ target: Target) -> some View {
        Group {
            Heading(text: "Drills")
            if let drills = target.recentDrills, !drills.isEmpty {
                ForEach(drills) { DrillRow(drill: $0, now: now) }
            } else {
                Text("None yet.").foregroundStyle(Retro.ink)
            }
        }
    }

    private func actions(_ target: Target) -> some View {
        Group {
            if target.isActive {
                Button(busy ? "Sending" : "Send a drill now") { Task { await sendNow() } }
                    .buttonStyle(RetroButtonStyle())
                    .disabled(busy || target.waitingDrill != nil)
                if target.waitingDrill != nil {
                    Text("One drill at a time. The button returns when this one is settled.")
                        .font(Retro.font(11))
                        .foregroundStyle(Retro.ink)
                }
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
            now = Date()
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func sendNow() async {
        await perform { try await $0.sendNow(target: targetID) }
    }

    private func resend() async {
        await perform { try await $0.resendCode(target: targetID) }
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

    /// Run one server call, then reload, with the buttons disabled meanwhile.
    private func perform(_ call: (API) async throws -> some Any) async {
        guard let api = API.configured else { return }
        busy = true
        defer { busy = false }
        do {
            _ = try await call(api)
            await load()
        } catch {
            self.error = error.localizedDescription
        }
    }
}
