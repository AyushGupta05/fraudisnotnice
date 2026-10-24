import Foundation

/// The Shortcut on this phone that sends whatever the server has queued.
/// The app never sends texts itself; it hands over to Shortcuts.
enum Pump {
    static let shortcutName = "Scam Check Pump"
    static let url = URL(string: "shortcuts://run-shortcut?name=Scam%20Check%20Pump")!
}
