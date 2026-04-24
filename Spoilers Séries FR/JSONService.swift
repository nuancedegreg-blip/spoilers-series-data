import Foundation

struct JSONService {
    private let remoteURL = URL(string: "https://spoilers-series-data.pages.dev/spoilers.json")

    func fetchData() async throws -> APIResponse {
        guard let remoteURL else {
            throw JSONServiceError.invalidURL
        }

        var request = URLRequest(url: remoteURL)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.timeoutInterval = 15

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw JSONServiceError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw JSONServiceError.httpStatus(httpResponse.statusCode)
        }

        return try JSONDecoder().decode(APIResponse.self, from: data)
    }
}

enum JSONServiceError: Error {
    case invalidURL
    case invalidResponse
    case httpStatus(Int)
}
