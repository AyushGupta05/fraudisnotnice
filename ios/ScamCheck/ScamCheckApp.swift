import SwiftUI

@main
struct ScamCheckApp: App {
    var body: some Scene {
        WindowGroup {
            HomeView()
                .preferredColorScheme(.dark)
                .tint(Retro.glow)
        }
    }
}
