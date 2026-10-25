import SwiftUI

/// Two steps: the questionnaire, then the six-digit code the person reads back.
struct EnrolView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var form = Enrolment()
    @State private var enrolled: Target?
    @State private var code = ""
    @State private var error: String?
    @State private var busy = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    if let enrolled {
                        codeStep(for: enrolled)
                    } else {
                        questionnaire
                    }
                    if let error {
                        Text(error).foregroundStyle(Retro.ink)
                    }
                }
                .padding(16)
            }
            .retroScreen()
            .retroTitle("Enrol")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("[X]") { dismiss() }
                        .font(Retro.font(14))
                        .foregroundStyle(Retro.glow)
                }
            }
        }
    }

    private var questionnaire: some View {
        Group {
            Heading(text: "About them")
            Field("What the family calls them", text: $form.name, prompt: "Nana")
            Field("Their mobile number", text: $form.phone, prompt: "07700 900123")
                .keyboardType(.phonePad)
            Field("Their bank", text: $form.bank, prompt: "Lloyds")
            Field("Parcel firm they use", text: $form.parcelFirm, prompt: "Evri")

            Heading(text: "About you")
            Field("Your name", text: $form.grandchild, prompt: "Ayush")
            Field("What they call you", text: $form.nickname, prompt: "Jamie")

            Button(busy ? "Sending" : "Send code") { Task { await enrol() } }
                .buttonStyle(RetroButtonStyle())
                .disabled(busy || !form.isComplete)
                .padding(.top, 8)
            Text("They get a text with a code. Reading it back is their yes.")
                .font(Retro.font(12, weight: .regular))
                .foregroundStyle(Retro.ink)
        }
    }

    private func codeStep(for target: Target) -> some View {
        Group {
            Text("A code has been texted to \(target.name). Type what they read back.")
                .retroBox()
            Field("Six-digit code", text: $code, prompt: "123456")
                .keyboardType(.numberPad)
            Button(busy ? "Checking" : "Confirm") { Task { await verify(target) } }
                .buttonStyle(RetroButtonStyle())
                .disabled(busy || code.count != 6)
        }
    }

    private func enrol() async {
        guard let api = API.configured else {
            error = "Add the server under SET first."
            return
        }
        busy = true
        defer { busy = false }
        do {
            enrolled = try await api.enrol(form)
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func verify(_ target: Target) async {
        guard let api = API.configured else { return }
        busy = true
        defer { busy = false }
        do {
            _ = try await api.verify(target: target.id, code: code)
            dismiss()
        } catch {
            self.error = error.localizedDescription
        }
    }
}
