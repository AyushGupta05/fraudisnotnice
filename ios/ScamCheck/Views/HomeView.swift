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
                        Text("Add the server address and token under SET.")
                            .retroBox()
                    } else if targets.isEmpty {
                        Text("Nobody enrolled yet.")
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
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(target.name.uppercased()).font(Retro.font(17))
                Spacer()
                Text(target.statusLine.uppercased()).font(Retro.font(12)).foregroundStyle(Retro.ink)
            }
            Text("\(Retro.meter(target.immunity)) \(Retro.percent(target.immunity))")
                .font(Retro.font(15))
            Text("STREAK \(target.streak)   PTS \(target.points)")
                .font(Retro.font(12))
                .foregroundStyle(Retro.ink)
        }
        .retroBox()
    }
}
