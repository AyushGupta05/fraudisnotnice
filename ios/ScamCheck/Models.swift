import Foundation

/// A person receiving drills. The list endpoint omits `byType` and `recentDrills`; the detail endpoint includes them.
struct Target: Codable, Identifiable {
    let id: Int
    let name: String
    let phone: String
    let grandchild: String
    let status: String          // pending | active | stopped
    let points: Int
    let streak: Int
    let immunity: Int?          // percentage of resolved drills left untouched
    let intervalHours: Int
    let windowHours: Double
    let nextDueAt: Date?
    let waitingDrill: Drill?    // a drill sent and not yet answered
    let byType: [String: TypeScore]?
    let recentDrills: [Drill]?

    var isActive: Bool { status == "active" }

    var statusLine: String {
        switch status {
        case "pending": "no code yet"
        case "stopped": "opted out"
        default: waitingDrill == nil ? "protected" : "drill out"
        }
    }
}

struct TypeScore: Codable {
    let label: String
    let attempts: Int
    let passed: Int
    let clicked: Int
    let immunity: Int?
}

struct Drill: Codable, Identifiable {
    let id: Int
    let scamType: String
    let label: String
    let status: String          // pending | passed | clicked
    let body: String
    let sentAt: Date
    let passesAt: Date?         // when a pending drill becomes a pass
    let resolvedAt: Date?

    /// How far a pending drill is through its window, 0 to 1.
    func progress(at now: Date) -> Double {
        guard let passesAt else { return 1 }
        let total = passesAt.timeIntervalSince(sentAt)
        return total > 0 ? min(max(now.timeIntervalSince(sentAt) / total, 0), 1) : 1
    }
}

/// The questionnaire. Field names match what the server expects once converted to snake_case.
struct Enrolment: Encodable {
    var name = ""
    var phone = ""
    var grandchild = ""
    var nickname = ""
    var bank = ""
    var parcelFirm = ""
    var wakeHour = 9
    var sleepHour = 21

    var isComplete: Bool { !name.isEmpty && !phone.isEmpty && !grandchild.isEmpty }
}
