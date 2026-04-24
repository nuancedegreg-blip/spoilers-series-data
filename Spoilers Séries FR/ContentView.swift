//
//  ContentView.swift
//  Spoilers Séries FR
//
//  Created by Greg on 24/04/2026.
//

import SwiftUI

struct ContentView: View {
    @AppStorage("favoriteSeriesIDs") private var favoriteSeriesIDs = ""
    @AppStorage("spoilerModeEnabled") private var spoilerModeEnabled = true
    @AppStorage("preferredAppearance") private var preferredAppearance = "system"
    @State private var viewModel = ContentViewModel()

    private let isPreview = ProcessInfo.processInfo.environment["XCODE_RUNNING_FOR_PREVIEWS"] == "1"

    var body: some View {
        TabView {
            NavigationStack {
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        headerCard

                        if let errorMessage = viewModel.errorMessage {
                            StatusCard(message: errorMessage)
                        }

                        if viewModel.isLoading {
                            HStack(spacing: 12) {
                                ProgressView()
                                Text("Actualisation en cours")
                                    .font(.subheadline.weight(.medium))
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding()
                            .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
                        }

                        VStack(alignment: .leading, spacing: 12) {
                            Text("Derniers spoilers")
                                .font(.title3.bold())

                            if latestSpoilers.isEmpty {
                                ContentUnavailableView("Aucun spoiler", systemImage: "sparkles.tv")
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 24)
                            } else {
                                ForEach(latestSpoilers) { spoiler in
                                    SpoilerCardView(
                                        spoiler: spoiler,
                                        series: series(for: spoiler.seriesID),
                                        spoilerModeEnabled: spoilerModeEnabled
                                    )
                                }
                            }
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.vertical, 16)
                }
                .background(AppBackgroundView())
                .navigationTitle("Accueil")
                .toolbar {
                    Button("Actualiser") {
                        Task {
                            await viewModel.refresh()
                        }
                    }
                    .disabled(viewModel.isLoading || isPreview)
                    .fontWeight(.semibold)
                }
            }
            .tabItem {
                Label("Accueil", systemImage: "house.fill")
            }

            NavigationStack {
                ScrollView {
                    LazyVStack(spacing: 14) {
                        ForEach(viewModel.spoilersData.series) { series in
                            NavigationLink {
                                SeriesDetailView(
                                    series: series,
                                    spoilers: spoilers(for: series.id),
                                    spoilerModeEnabled: spoilerModeEnabled
                                )
                            } label: {
                                SeriesCardView(
                                    series: series,
                                    spoilerCount: spoilers(for: series.id).count,
                                    isFavorite: isFavorite(series.id)
                                )
                            }
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.vertical, 16)
                }
                .background(AppBackgroundView())
                .navigationTitle("Séries")
                .overlay {
                    if viewModel.spoilersData.series.isEmpty && viewModel.isLoading == false {
                        ContentUnavailableView("Aucune série", systemImage: "tv")
                    }
                }
            }
            .tabItem {
                Label("Séries", systemImage: "tv.fill")
            }

            NavigationStack {
                ScrollView {
                    VStack(alignment: .leading, spacing: 14) {
                        ForEach(calendarSpoilers) { spoiler in
                            SpoilerCardView(
                                spoiler: spoiler,
                                series: series(for: spoiler.seriesID),
                                spoilerModeEnabled: spoilerModeEnabled,
                                showsDate: true
                            )
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.vertical, 16)
                }
                .background(AppBackgroundView())
                .navigationTitle("Calendrier")
                .overlay {
                    if calendarSpoilers.isEmpty {
                        ContentUnavailableView("Aucune date disponible", systemImage: "calendar")
                    }
                }
            }
            .tabItem {
                Label("Calendrier", systemImage: "calendar")
            }

            NavigationStack {
                ScrollView {
                    VStack(alignment: .leading, spacing: 14) {
                        if favoriteSeries.isEmpty {
                            ContentUnavailableView("Aucun favori", systemImage: "heart")
                                .frame(maxWidth: .infinity)
                                .padding(.top, 80)
                        } else {
                            ForEach(favoriteSeries) { series in
                                NavigationLink {
                                    SeriesDetailView(
                                        series: series,
                                        spoilers: spoilers(for: series.id),
                                        spoilerModeEnabled: spoilerModeEnabled
                                    )
                                } label: {
                                    SeriesCardView(
                                        series: series,
                                        spoilerCount: spoilers(for: series.id).count,
                                        isFavorite: true
                                    )
                                }
                            }
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.vertical, 16)
                }
                .background(AppBackgroundView())
                .navigationTitle("Favoris")
            }
            .tabItem {
                Label("Favoris", systemImage: "heart.fill")
            }

            NavigationStack {
                SettingsView(
                    spoilerModeEnabled: $spoilerModeEnabled,
                    preferredAppearance: $preferredAppearance
                )
            }
            .tabItem {
                Label("Réglages", systemImage: "gearshape.fill")
            }
        }
        .preferredColorScheme(colorSchemePreference)
        .task {
            guard isPreview == false else {
                return
            }

            await viewModel.loadIfNeeded()
        }
    }

    private var headerCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Spoilers Séries FR")
                        .font(.largeTitle.bold())

                    Text("Derniers résumés et spoilers dans une interface native, rapide et lisible.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                Image(systemName: "sparkles.tv")
                    .font(.title2.weight(.semibold))
                    .foregroundStyle(.white)
                    .padding(12)
                    .background(
                        LinearGradient(
                            colors: [.blue, .indigo],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        in: RoundedRectangle(cornerRadius: 16, style: .continuous)
                    )
            }

            Group {
                if let lastUpdate = viewModel.lastUpdate {
                    Label(
                        "Mis à jour \(lastUpdate.formatted(date: .abbreviated, time: .shortened))",
                        systemImage: "clock"
                    )
                } else {
                    Label("Aucune mise à jour enregistrée", systemImage: "clock.badge.questionmark")
                }
            }
            .font(.footnote.weight(.medium))
            .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(20)
        .background(
            LinearGradient(
                colors: [
                    Color(uiColor: .secondarySystemBackground),
                    Color(uiColor: .systemBackground)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            ),
            in: RoundedRectangle(cornerRadius: 28, style: .continuous)
        )
        .overlay {
            RoundedRectangle(cornerRadius: 28, style: .continuous)
                .stroke(Color.primary.opacity(0.06), lineWidth: 1)
        }
        .shadow(color: .black.opacity(0.06), radius: 16, y: 8)
    }

    private var latestSpoilers: [Spoiler] {
        Array(viewModel.spoilersData.spoilers.prefix(3))
    }

    private var calendarSpoilers: [Spoiler] {
        viewModel.spoilersData.spoilers.sorted {
            spoilerDate(for: $0)?.timeIntervalSince1970 ?? .greatestFiniteMagnitude <
            spoilerDate(for: $1)?.timeIntervalSince1970 ?? .greatestFiniteMagnitude
        }
    }

    private var favoriteSeries: [Series] {
        viewModel.spoilersData.series.filter { favoriteIDSet.contains($0.id) }
    }

    private var colorSchemePreference: ColorScheme? {
        switch preferredAppearance {
        case "light":
            return .light
        case "dark":
            return .dark
        default:
            return nil
        }
    }

    private func series(for id: String) -> Series? {
        viewModel.spoilersData.series.first { $0.id == id }
    }

    private func spoilers(for seriesID: String) -> [Spoiler] {
        viewModel.spoilersData.spoilers.filter { $0.seriesID == seriesID }
    }

    private func spoilerDate(for spoiler: Spoiler) -> Date? {
        SpoilerDateFormatter.shared.date(from: spoiler.date)
    }

    private func isFavorite(_ seriesID: String) -> Bool {
        favoriteIDSet.contains(seriesID)
    }

    private var favoriteIDSet: Set<String> {
        Set(
            favoriteSeriesIDs
                .split(separator: ",")
                .map(String.init)
        )
    }
}

#Preview {
    ContentView()
}

struct SeriesDetailView: View {
    @AppStorage("favoriteSeriesIDs") private var favoriteSeriesIDs = ""

    let series: Series
    let spoilers: [Spoiler]
    let spoilerModeEnabled: Bool

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                VStack(alignment: .leading, spacing: 10) {
                    Text(series.title)
                        .font(.largeTitle.bold())

                    HStack(spacing: 10) {
                        SpoilerBadge()
                        Text("\(spoilers.count) spoiler\(spoilers.count > 1 ? "s" : "")")
                            .font(.subheadline.weight(.medium))
                            .foregroundStyle(.secondary)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(20)
                .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 24, style: .continuous))

                if spoilers.isEmpty {
                    ContentUnavailableView("Aucun spoiler", systemImage: "text.page.slash")
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 40)
                } else {
                    ForEach(spoilers) { spoiler in
                        SpoilerCardView(
                            spoiler: spoiler,
                            series: nil,
                            spoilerModeEnabled: spoilerModeEnabled,
                            showsDate: true
                        )
                    }
                }
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 16)
        }
        .background(AppBackgroundView())
        .navigationTitle(series.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            Button {
                toggleFavorite()
            } label: {
                Image(systemName: isFavorite ? "heart.fill" : "heart")
                    .foregroundStyle(isFavorite ? .red : .primary)
            }
        }
    }

    private var isFavorite: Bool {
        favoriteIDSet.contains(series.id)
    }

    private var favoriteIDSet: Set<String> {
        Set(
            favoriteSeriesIDs
                .split(separator: ",")
                .map(String.init)
        )
    }

    private func toggleFavorite() {
        var updatedFavorites = favoriteIDSet

        if updatedFavorites.contains(series.id) {
            updatedFavorites.remove(series.id)
        } else {
            updatedFavorites.insert(series.id)
        }

        favoriteSeriesIDs = updatedFavorites
            .sorted()
            .joined(separator: ",")
    }
}

private struct SeriesCardView: View {
    let series: Series
    let spoilerCount: Int
    let isFavorite: Bool

    var body: some View {
        HStack(spacing: 14) {
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [.blue, .cyan],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .frame(width: 56, height: 56)
                .overlay {
                    Image(systemName: "tv")
                        .font(.title3.weight(.semibold))
                        .foregroundStyle(.white)
                }

            VStack(alignment: .leading, spacing: 8) {
                Text(series.title)
                    .font(.headline)
                    .foregroundStyle(.primary)

                Text(series.description)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)

                HStack(spacing: 8) {
                    SpoilerBadge()

                    Text("\(spoilerCount) contenu\(spoilerCount > 1 ? "s" : "")")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }

            Spacer()

            if isFavorite {
                Image(systemName: "heart.fill")
                    .foregroundStyle(.red)
            }
        }
        .padding(16)
        .background(
            Color(uiColor: .secondarySystemBackground),
            in: RoundedRectangle(cornerRadius: 24, style: .continuous)
        )
        .overlay {
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .stroke(Color.primary.opacity(0.05), lineWidth: 1)
        }
    }
}

private struct SpoilerCardView: View {
    let spoiler: Spoiler
    let series: Series?
    let spoilerModeEnabled: Bool
    var showsDate: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 8) {
                    if let series {
                        Text(series.title)
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.secondary)
                    }

                    Text(spoiler.title)
                        .font(.headline)
                        .foregroundStyle(.primary)

                    if showsDate, let formattedDate = spoiler.formattedDate {
                        Label(formattedDate, systemImage: "calendar")
                            .font(.caption.weight(.medium))
                            .foregroundStyle(.secondary)
                    }
                }

                Spacer()

                SpoilerBadge(title: spoiler.category)
            }

            Text(spoiler.content)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.leading)
                .redacted(reason: spoilerModeEnabled ? [] : .placeholder)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .background(
            Color(uiColor: .secondarySystemBackground),
            in: RoundedRectangle(cornerRadius: 24, style: .continuous)
        )
        .overlay {
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .stroke(Color.primary.opacity(0.05), lineWidth: 1)
        }
    }
}

private struct SpoilerBadge: View {
    let title: String

    init(title: String = "Spoiler") {
        self.title = title
    }

    var body: some View {
        Text(title)
            .font(.caption.bold())
            .foregroundStyle(.white)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(
                LinearGradient(
                    colors: [.pink, .red],
                    startPoint: .leading,
                    endPoint: .trailing
                ),
                in: Capsule()
            )
    }
}

private struct StatusCard: View {
    let message: String

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "wifi.slash")
                .foregroundStyle(.orange)

            Text(message)
                .font(.subheadline)
                .foregroundStyle(.primary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(Color.orange.opacity(0.12), in: RoundedRectangle(cornerRadius: 20, style: .continuous))
    }
}

private struct SettingsView: View {
    @Binding var spoilerModeEnabled: Bool
    @Binding var preferredAppearance: String

    var body: some View {
        List {
            Section("Lecture") {
                Toggle("Mode spoiler", isOn: $spoilerModeEnabled)

                Picker("Apparence", selection: $preferredAppearance) {
                    Text("Système").tag("system")
                    Text("Clair").tag("light")
                    Text("Sombre").tag("dark")
                }
            }

            Section("Informations") {
                NavigationLink("Application non officielle") {
                    InfoPageView(
                        title: "Application non officielle",
                        text: "Spoilers Séries FR est une application indépendante. Elle n'est affiliée à aucune chaîne, plateforme ou société de production."
                    )
                }

                NavigationLink("Confidentialité") {
                    InfoPageView(
                        title: "Confidentialité",
                        text: "Les favoris et préférences sont stockés localement sur l'appareil. Aucun compte n'est requis à ce stade."
                    )
                }

                NavigationLink("Sources") {
                    InfoPageView(
                        title: "Sources",
                        text: "Les contenus affichés proviennent d'un fichier JSON administré par l'éditeur de l'application. Aucun scraping ni reprise de logos n'est utilisé."
                    )
                }
            }

            Section("Publicité") {
                AdPlaceholderView()
            }
        }
        .navigationTitle("Réglages")
    }
}

private struct InfoPageView: View {
    let title: String
    let text: String

    var body: some View {
        ScrollView {
            Text(text)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(20)
        }
        .background(AppBackgroundView())
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
    }
}

private struct AdPlaceholderView: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Emplacement publicité")
                .font(.headline)
            Text("Zone réservée pour AdMob. Intégration non activée.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(Color.secondary.opacity(0.12))
                .frame(height: 72)
                .overlay {
                    Text("Bannière inactive")
                        .font(.footnote.weight(.medium))
                        .foregroundStyle(.secondary)
                }
        }
        .padding(.vertical, 4)
    }
}

private struct AppBackgroundView: View {
    var body: some View {
        LinearGradient(
            colors: [
                Color(uiColor: .systemBackground),
                Color.blue.opacity(0.08),
                Color(uiColor: .systemBackground)
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
        .ignoresSafeArea()
    }
}

private enum SpoilerDateFormatter {
    static let shared: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.locale = Locale(identifier: "fr_FR")
        return formatter
    }()

    static let display: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .none
        formatter.locale = Locale(identifier: "fr_FR")
        return formatter
    }()
}

private extension Spoiler {
    var formattedDate: String? {
        guard let parsedDate = SpoilerDateFormatter.shared.date(from: date) else {
            return nil
        }

        return SpoilerDateFormatter.display.string(from: parsedDate)
    }
}
