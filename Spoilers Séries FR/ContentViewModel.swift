import Foundation
import Observation

@MainActor
@Observable
final class ContentViewModel {
    private(set) var spoilersData: SpoilersData
    private(set) var isLoading = false
    private(set) var lastUpdate: Date?
    private(set) var errorMessage: String?

    private let jsonService = JSONService()
    private var hasLoaded = false

    init() {
        spoilersData = CacheManager.loadSpoilersData() ?? LocalJSONLoader.loadSpoilersData()
        lastUpdate = CacheManager.loadLastUpdate() ?? Self.parseDate(from: spoilersData.lastUpdate)
    }

    func loadIfNeeded() async {
        guard hasLoaded == false, isLoading == false else {
            return
        }

        hasLoaded = true
        await refresh()
    }

    func refresh() async {
        guard isLoading == false else {
            return
        }

        isLoading = true
        errorMessage = nil

        defer {
            isLoading = false
        }

        do {
            let remoteData = try await jsonService.fetchData()
            spoilersData = remoteData
            CacheManager.saveSpoilersData(remoteData)
            lastUpdate = Self.parseDate(from: remoteData.lastUpdate) ?? CacheManager.loadLastUpdate()
        } catch {
            if let cachedData = CacheManager.loadSpoilersData() {
                spoilersData = cachedData
                lastUpdate = CacheManager.loadLastUpdate() ?? Self.parseDate(from: cachedData.lastUpdate)
                errorMessage = "Connexion impossible. Affichage du dernier cache local."
            } else if spoilersData.series.isEmpty && spoilersData.spoilers.isEmpty {
                spoilersData = LocalJSONLoader.loadSpoilersData()
                lastUpdate = Self.parseDate(from: spoilersData.lastUpdate)
                errorMessage = "Connexion impossible. Affichage des données locales embarquées."
            } else {
                errorMessage = "Connexion impossible. Les données actuellement affichées sont conservées."
            }
        }
    }

    private static func parseDate(from value: String) -> Date? {
        guard value.isEmpty == false else {
            return nil
        }

        return APIResponseDateFormatter.shared.date(from: value)
    }
}

private enum APIResponseDateFormatter {
    static let shared: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.locale = Locale(identifier: "fr_FR")
        return formatter
    }()
}
