import SwiftUI

struct SettingsView: View {
    @AppStorage("serverURL") private var serverURL = ""
    @AppStorage("token") private var token = ""
    @State private var family: [FamilyMember] = []
    @State private var newName = ""
    @State private var newPhone = ""
    @State private var error: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                Heading(text: "Server")
                Field("Address", text: $serverURL, prompt: "https://....trycloudflare.com")
                    .keyboardType(.URL)
                    .textInputAutocapitalization(.never)
                Field("Token", text: $token, prompt: "")
                    .textInputAutocapitalization(.never)

                Heading(text: "Family to alert")
                ForEach(family) { member in
                    HStack {
                        Text(member.name.uppercased()).font(Retro.font(13))
                        Spacer()
                        Text(member.phone).font(Retro.font(13, weight: .regular)).foregroundStyle(Retro.ink)
                        Button("[X]") { Task { await remove(member) } }
                            .font(Retro.font(13))
                    }
                }
                Field("Name", text: $newName, prompt: "Mum")
                Field("Mobile", text: $newPhone, prompt: "07700 900001")
                    .keyboardType(.phonePad)
                Button("Add") { Task { await add() } }
                    .buttonStyle(RetroButtonStyle(filled: false))
                    .disabled(newName.isEmpty || newPhone.isEmpty)

                if let error {
                    Text(error).foregroundStyle(Retro.ink)
                }
            }
            .padding(16)
        }
        .retroScreen()
        .retroTitle("Settings")
        .task { await loadFamily() }
        .onChange(of: serverURL) { Task { await loadFamily() } }
        .onChange(of: token) { Task { await loadFamily() } }
    }

    private func loadFamily() async {
        guard let api = API.configured else { return }
        do {
            family = try await api.family()
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func add() async {
        guard let api = API.configured else { return }
        do {
            family = try await api.addFamily(name: newName, phone: newPhone)
            newName = ""
            newPhone = ""
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func remove(_ member: FamilyMember) async {
        guard let api = API.configured else { return }
        do {
            try await api.removeFamily(member.id)
            family.removeAll { $0.id == member.id }
        } catch {
            self.error = error.localizedDescription
        }
    }
}
