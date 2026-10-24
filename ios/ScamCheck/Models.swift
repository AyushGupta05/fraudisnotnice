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
    let immunity: Int?          // percentage of resolved drills that were forwarded
    let intervalHours: Int
    let nextDueAt: Date?
    let waitingDrill: Drill?    // a drill sent and not yet answered
    let byType: [String: TypeScore]?
    let recentDrills: [Drill]?

    var isActive: Bool { status == "active" }

    var statusLine: String {
        switch status {
        case "pending": "awaiting code"
        case "stopped": "opted out"
        default: waitingDrill == nil ? "active" : "drill out"
        }
    }
}

struct TypeScore: Codable {
    let label: String
    let attempts: Int
    let forwarded: Int
    let clicked: Int
    let missed: Int
    let immunity: Int?
}

struct Drill: Codable, Identifiable {
    let id: Int
    let scamType: String
    let label: String
    let status: String          // pending | forwarded | clicked | missed
    let body: String
    let sentAt: Date
    let resolvedAt: Date?
}

struct FamilyMember: Codable, Identifiable {
    let id: Int
    let name: String
    let phone: String
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
