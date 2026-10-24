import Foundation

/// Talks to the Flask server. Holds no state, so make one wherever it is needed.
struct API {
    let baseURL: URL
    let token: String

    /// nil until a server address and token have been entered in Settings.
    static var configured: API? {
        let defaults = UserDefaults.standard
        guard let address = defaults.string(forKey: "serverURL"), let url = URL(string: address),
              let token = defaults.string(forKey: "token"), !token.isEmpty else { return nil }
        return API(baseURL: url, token: token)
    }

    struct ServerError: LocalizedError {
        let message: String
        var errorDescription: String? { message }
    }

    func targets() async throws -> [Target] { try await send("GET", "targets") }
    func target(_ id: Int) async throws -> Target { try await send("GET", "targets/\(id)") }
    func enrol(_ form: Enrolment) async throws -> Target { try await send("POST", "enrol", form) }
    func verify(target id: Int, code: String) async throws -> Target {
        try await send("POST", "verify", Verification(targetId: id, code: code))
    }
    func sendNow(target id: Int) async throws -> Drill { try await send("POST", "targets/\(id)/send-now") }
    func forget(target id: Int) async throws { let _: Deleted = try await send("DELETE", "targets/\(id)") }

    func family() async throws -> [FamilyMember] { try await send("GET", "family") }
    func addFamily(name: String, phone: String) async throws -> [FamilyMember] {
        try await send("POST", "family", ["name": name, "phone": phone])
    }
    func removeFamily(_ id: Int) async throws { let _: Deleted = try await send("DELETE", "family/\(id)") }

    // MARK: - Wire format

    private struct Verification: Encodable { let targetId: Int; let code: String }
    private struct Deleted: Decodable { let deleted: Int }
    private struct Failure: Decodable { let error: String }

    private static let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        return encoder
    }()

    private static let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }()

    private func send<Response: Decodable>(_ method: String, _ path: String, _ body: (any Encodable)? = nil) async throws -> Response {
        var request = URLRequest(url: baseURL.appending(path: path))
        request.httpMethod = method
        request.setValue(token, forHTTPHeaderField: "X-Token")
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try Self.encoder.encode(body)
        }

        let (data, response) = try await URLSession.shared.data(for: request)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200..<300).contains(status) else {
            let failure = try? Self.decoder.decode(Failure.self, from: data)
            throw ServerError(message: failure?.error ?? "Server returned \(status)")
        }
        return try Self.decoder.decode(Response.self, from: data)
    }
}
