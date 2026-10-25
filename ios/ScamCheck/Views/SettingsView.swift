import SwiftUI

struct SettingsView: View {
    @AppStorage("serverURL") private var serverURL = ""
    @AppStorage("token") private var token = ""
    @State private var result: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                Heading(text: "Server")
                Field("Address printed by run.sh", text: $serverURL, prompt: "https://....trycloudflare.com")
                    .keyboardType(.URL)
                    .textInputAutocapitalization(.never)
                Field("Token from server/.env", text: $token, prompt: "")
                    .textInputAutocapitalization(.never)
                Button("Test connection") { Task { await test() } }
                    .buttonStyle(RetroButtonStyle(filled: false))
                    .disabled(API.configured == nil)
                if let result {
                    Text(result).font(Retro.font(12)).foregroundStyle(Retro.ink)
                }
            }
            .padding(16)
        }
        .retroScreen()
        .retroTitle("Settings")
        .onChange(of: serverURL) { result = nil }
        .onChange(of: token) { result = nil }
    }

    private func test() async {
        guard let api = API.configured else { return }
        do {
            let health = try await api.health()
            _ = try await api.targets()
            result = "Connected. Drill links use \(health.linkBase)."
        } catch {
            result = "Not connected: \(error.localizedDescription)"
        }
    }
}
