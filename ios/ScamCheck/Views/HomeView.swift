import SwiftUI

struct HomeView: View {
    @State private var targets: [Target] = []
    @State private var error: String?
    @State private var enrolling = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if API.configured == nil {
                        Text("Add the server address and token under SET to begin.")
                            .retroBox()
                    } else if targets.isEmpty && error == nil {
                        Text("Nobody enrolled yet. Enrol someone and they get a code by text.")
                            .retroBox()
                    }

                    ForEach(targets) { target in
                        NavigationLink(value: target.id) {
                            TargetCard(target: target)
                        }
                    }

                    if let error {
                        Text(error).foregroundStyle(Retro.ink)
                    }

                    Button("Enrol someone") { enrolling = true }
                        .buttonStyle(RetroButtonStyle())
                        .disabled(API.configured == nil)
                }
                .padding(16)
            }
            .retroScreen()
            .retroTitle("Scam Check")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    NavigationLink {
                        SettingsView()
                    } label: {
                        Text("[SET]").font(Retro.font(14)).foregroundStyle(Retro.glow)
                    }
                }
            }
            .navigationDestination(for: Int.self) { id in
                TargetView(targetID: id)
            }
            .refreshable { await load() }
            .onAppear { Task { await load() } }
            .sheet(isPresented: $enrolling, onDismiss: { Task { await load() } }) {
                EnrolView()
            }
        }
    }

    private func load() async {
        guard let api = API.configured else { return }
        do {
            targets = try await api.targets()
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }
}

struct TargetCard: View {
    let target: Target

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(target.name.uppercased()).font(Retro.font(17))
                Spacer()
                Badge(text: target.statusLine, filled: target.waitingDrill != nil)
            }
            HStack(spacing: 10) {
                Bar(fraction: target.immunity.map { Double($0) / 100 })
                Text(Retro.percent(target.immunity)).font(Retro.font(13))
            }
            Text(detailLine)
                .font(Retro.font(12))
                .foregroundStyle(Retro.ink)
        }
        .retroBox()
    }

    private var detailLine: String {
        if target.status == "pending" { return "Waiting for them to read the code back" }
        if let waiting = target.waitingDrill, let passesAt = waiting.passesAt {
            return "Drill out. Pass \(passesAt.formatted(.relative(presentation: .named))) if untouched"
        }
        if let due = target.nextDueAt { return "Streak \(target.streak)  ·  Next drill \(due.formatted(.relative(presentation: .named)))" }
        return "Streak \(target.streak)"
    }
}
