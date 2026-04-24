import Foundation

struct APIResponse: Codable {
    let lastUpdate: String
    let series: [Series]
    let spoilers: [Spoiler]
}

typealias SpoilersData = APIResponse
