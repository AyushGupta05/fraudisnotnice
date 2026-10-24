import SwiftUI

/// The four greens of an original Game Boy screen, and the few shapes every screen is built from.
enum Retro {
    static let screen = Color(red: 15 / 255, green: 56 / 255, blue: 15 / 255)
    static let shadow = Color(red: 48 / 255, green: 98 / 255, blue: 48 / 255)
    static let ink = Color(red: 139 / 255, green: 172 / 255, blue: 15 / 255)
    static let glow = Color(red: 155 / 255, green: 188 / 255, blue: 15 / 255)

    static func font(_ size: CGFloat, weight: Font.Weight = .bold) -> Font {
        .system(size: size, weight: weight, design: .monospaced)
    }

    /// A ten-block meter like ▮▮▮▮▮▮▯▯▯▯ for a percentage, or dots when there is no score yet.
    static func meter(_ percent: Int?) -> String {
        guard let percent else { return String(repeating: "·", count: 10) }
        let filled = Int((Double(percent) / 10).rounded())
        return String(repeating: "▮", count: filled) + String(repeating: "▯", count: 10 - filled)
    }

    static func percent(_ value: Int?) -> String {
        value.map { "\($0)%" } ?? "--"
    }
}

/// Section heading in the style of an old menu: "▶ TARGETS"
struct Heading: View {
    let text: String

    var body: some View {
        Text("▶ " + text.uppercased())
            .font(Retro.font(13))
            .foregroundStyle(Retro.ink)
            .padding(.top, 6)
    }
}

/// A labelled text box.
struct Field: View {
    let label: String
    @Binding var text: String
    let prompt: String

    init(_ label: String, text: Binding<String>, prompt: String) {
        self.label = label
        self._text = text
        self.prompt = prompt
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label.uppercased())
                .font(Retro.font(11))
                .foregroundStyle(Retro.ink)
            TextField("", text: $text, prompt: Text(prompt).foregroundStyle(Retro.shadow))
                .font(Retro.font(16, weight: .regular))
                .padding(10)
                .background(Retro.shadow.opacity(0.35))
                .overlay(Rectangle().stroke(Retro.ink, lineWidth: 2))
                .autocorrectionDisabled()
        }
    }
}

struct RetroButtonStyle: ButtonStyle {
    var filled = true

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(Retro.font(15))
            .textCase(.uppercase)
            .padding(.vertical, 12)
            .frame(maxWidth: .infinity)
            .background(filled ? Retro.glow : Retro.screen)
            .foregroundStyle(filled ? Retro.screen : Retro.glow)
            .overlay(Rectangle().stroke(Retro.glow, lineWidth: 3))
            .opacity(configuration.isPressed ? 0.6 : 1)
    }
}

extension View {
    /// A bordered panel.
    func retroBox() -> some View {
        self
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .overlay(Rectangle().stroke(Retro.glow, lineWidth: 3))
    }

    /// Dark green screen, light green text. Applied once per screen.
    func retroScreen() -> some View {
        self
            .font(Retro.font(15, weight: .regular))
            .foregroundStyle(Retro.glow)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Retro.screen.ignoresSafeArea())
            .toolbarBackground(Retro.screen, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
    }

    /// Title text in the navigation bar.
    func retroTitle(_ text: String) -> some View {
        self
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Text(text.uppercased())
                        .font(Retro.font(18))
                        .foregroundStyle(Retro.glow)
                }
            }
    }
}
