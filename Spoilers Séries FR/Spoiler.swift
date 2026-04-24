import Foundation

struct Spoiler: Identifiable, Codable {
    let id: String
    let seriesID: String
    let title: String
    let content: String
    let date: String
    let category: String

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case content
        case seriesID = "series_id"
        case date
        case category
    }
}
