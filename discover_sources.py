#!/usr/bin/env python3
"""Discover potential sources with strict legal defaults.

Discovery never makes a source publishable by itself. The classifier is
intentionally conservative: anything even slightly ambiguous stays unknown.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request


ROOT_DIR = Path(__file__).resolve().parent
DISCOVERED_SOURCES_PATH = ROOT_DIR / "discovered_sources.json"

SERIES_QUERIES = {
    "demain_nous_appartient": [
        "Demain nous appartient RSS officiel",
        "Demain nous appartient API officielle",
        "Demain nous appartient communique presse officiel",
    ],
    "ici_tout_commence": [
        "Ici tout commence RSS officiel",
        "Ici tout commence API officielle",
        "Ici tout commence communique presse officiel",
    ],
    "plus_belle_la_vie": [
        "Plus belle la vie RSS officiel",
        "Plus belle la vie API officielle",
        "Plus belle la vie communique presse officiel",
    ],
    "un_si_grand_soleil": [
        "Un si grand soleil RSS officiel",
        "Un si grand soleil API officielle",
        "Un si grand soleil communique presse officiel",
    ],
}

ALLOWED_PATTERNS = [
    re.compile(r"rss", re.IGNORECASE),
    re.compile(r"\.xml($|\?)", re.IGNORECASE),
    re.compile(r"\.json($|\?)", re.IGNORECASE),
    re.compile(r"/api/", re.IGNORECASE),
]

OFFICIAL_DOMAIN_HINTS = (
    "tf1",
    "france.tv",
    "francetelevisions",
    "m6",
    "groupe-tf1",
    "mytf1",
)

FORBIDDEN_PATTERNS = [
    re.compile(r"/login", re.IGNORECASE),
    re.compile(r"/compte", re.IGNORECASE),
    re.compile(r"/account", re.IGNORECASE),
    re.compile(r"paywall", re.IGNORECASE),
]


def write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def web_search(query: str) -> list[dict[str, str]]:
    endpoint = "https://duckduckgo.com/html/?" + parse.urlencode({"q": query})
    req = request.Request(endpoint, headers={"User-Agent": "SpoilersSeriesDiscovery/1.0"})
    try:
        with request.urlopen(req, timeout=20) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except error.URLError:
        return []

    results: list[dict[str, str]] = []
    for line in html.splitlines():
        if 'result__a' not in line or 'href="' not in line:
            continue
        href_part = line.split('href="', 1)[1]
        href = href_part.split('"', 1)[0]
        title = line.split(">", 1)[1].split("<", 1)[0].strip()
        if href and title:
            results.append({"title": title, "url": href})
        if len(results) >= 5:
            break
    return results


def detect_source_type(url: str) -> str:
    lowered = url.lower()
    if "rss" in lowered or lowered.endswith(".xml"):
        return "rss"
    if "api" in lowered or lowered.endswith(".json"):
        return "api"
    if "presse" in lowered or "press" in lowered or "communique" in lowered:
        return "public_press_release"
    return "web_page"


def classify_legality(url: str, source_type: str) -> tuple[str, str]:
    lowered = url.lower()

    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(lowered):
            return "forbidden", "URL appears gated, account-based or protected."

    if source_type in {"rss", "api"}:
        looks_structured = any(pattern.search(lowered) for pattern in ALLOWED_PATTERNS)
        looks_official = any(hint in lowered for hint in OFFICIAL_DOMAIN_HINTS)
        has_legal_notice = any(token in lowered for token in ("cgu", "terms", "privacy", "legal", "mentions-legales"))

        if looks_structured and looks_official and not has_legal_notice:
            return "allowed", "Structured endpoint on an official-looking domain with no obvious restriction."

        return "unknown", "Structured source found, but legal reuse remains unclear and needs manual review."

    if source_type == "public_press_release":
        return "unknown", "Official press/public page found, but legal reuse requires manual validation."

    return "unknown", "Potential source found, but legal and technical status are unclear."


def discover_sources() -> dict[str, Any]:
    items: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for series_id, queries in SERIES_QUERIES.items():
        for query in queries:
            for result in web_search(query):
                url = result["url"]
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                source_type = detect_source_type(url)
                legal_status, notes = classify_legality(url, source_type)

                items.append(
                    {
                        "name": result["title"],
                        "series_id": series_id,
                        "source_type": source_type,
                        "url": url,
                        "legal_status": legal_status,
                        "enabled": False if legal_status != "allowed" else True,
                        "discovery_query": query,
                        "notes": notes,
                    }
                )

    return {
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }


def main() -> int:
    payload = discover_sources()
    write_json(DISCOVERED_SOURCES_PATH, payload)
    print(f"[info] Wrote {DISCOVERED_SOURCES_PATH}")
    print(f"[info] Discovered {len(payload['items'])} potential source(s)")
    allowed = sum(1 for item in payload["items"] if item["legal_status"] == "allowed")
    unknown = sum(1 for item in payload["items"] if item["legal_status"] == "unknown")
    forbidden = sum(1 for item in payload["items"] if item["legal_status"] == "forbidden")
    print(f"[info] allowed={allowed} unknown={unknown} forbidden={forbidden}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
