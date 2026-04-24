import Foundation

enum LocalJSONLoader {
    static func loadSpoilersData() -> SpoilersData {
        guard let url = Bundle.main.url(forResource: "spoilers", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let spoilersData = try? JSONDecoder().decode(SpoilersData.self, from: data) else {
            return SpoilersData(lastUpdate: "", series: [], spoilers: [])
        }

        return spoilersData
    }
}
