import Foundation

/// The Shortcut on this phone that sends whatever the server has queued.
/// The app never sends texts itself: it runs the shortcut, which hands control straight back.
enum Pump {
    static let shortcutName = "Scam Check Pump"

    static let url: URL = {
        var parts = URLComponents(string: "shortcuts://x-callback-url/run-shortcut")!
        parts.queryItems = [
            URLQueryItem(name: "name", value: shortcutName),
            URLQueryItem(name: "x-success", value: "scamcheck://"),
            URLQueryItem(name: "x-error", value: "scamcheck://"),
        ]
        return parts.url!
    }()
}
