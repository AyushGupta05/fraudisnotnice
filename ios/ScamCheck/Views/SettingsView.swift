import SwiftUI

struct SettingsView: View {
    @AppStorage("serverURL") private var serverURL = ""
    @AppStorage("token") private var token = ""

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                Heading(text: "Server")
                Field("Address", text: $serverURL, prompt: "https://....trycloudflare.com")
                    .keyboardType(.URL)
                    .textInputAutocapitalization(.never)
                Field("Token", text: $token, prompt: "")
                    .textInputAutocapitalization(.never)
            }
            .padding(16)
        }
        .retroScreen()
        .retroTitle("Settings")
    }
}
