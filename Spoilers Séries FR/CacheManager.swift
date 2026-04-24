import Foundation

enum CacheManager {
    private static let cacheFileName = "spoilers_cache.json"
    private static let lastUpdateKey = "spoilersLastUpdate"

    static func loadSpoilersData() -> SpoilersData? {
        guard let data = try? Data(contentsOf: cacheFileURL) else {
            return nil
        }

        return try? JSONDecoder().decode(SpoilersData.self, from: data)
    }

    static func saveSpoilersData(_ spoilersData: SpoilersData) {
        guard let data = try? JSONEncoder().encode(spoilersData) else {
            return
        }

        try? data.write(to: cacheFileURL, options: .atomic)
        UserDefaults.standard.set(Date(), forKey: lastUpdateKey)
    }

    static func loadLastUpdate() -> Date? {
        UserDefaults.standard.object(forKey: lastUpdateKey) as? Date
    }

    private static var cacheFileURL: URL {
        let cachesDirectory = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first
            ?? FileManager.default.temporaryDirectory

        return cachesDirectory.appendingPathComponent(cacheFileName)
    }
}
