#!/usr/bin/env python3
"""Legal-first automatic spoiler generation from authorized sources only."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request
import xml.etree.ElementTree as ET


ROOT_DIR = Path(__file__).resolve().parent
SOURCES_PATH = ROOT_DIR / "sources.json"
INTERNAL_LOG_PATH = ROOT_DIR / "internal_sources.json"
OPENAI_API_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
DEFAULT_MAX_PER_DAY = int(os.environ.get("MAX_SPOILERS_PER_DAY", "3"))
DEFAULT_ITEM_LIMIT = int(os.environ.get("SOURCE_ITEM_LIMIT", "3"))
DEFAULT_OUTPUT_CANDIDATES = [
    ROOT_DIR / "spoilers.json",
    ROOT_DIR / "Spoilers Séries FR" / "Spoilers Séries FR" / "spoilers.json",
]
MIN_FACTS_REQUIRED = 2
WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9']+")
ALLOWED_SOURCE_TYPES = {"rss", "api", "manual_notes", "public_press_release"}


class GenerationError(Exception):
    pass


@dataclass
class FactRecord:
    source_id: str
    source_name: str
    source_link: str
    series_id: str
    category: str
    date: str
    source_type: str
    facts: list[str]

    @property
    def facts_hash(self) -> str:
        joined = "|".join(self.facts).strip().lower()
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate legal-safe spoilers from allowed sources only.")
    parser.add_argument("--sources", default=str(SOURCES_PATH), help="Path to sources.json")
    parser.add_argument("--output", default=os.environ.get("SPOILERS_JSON_PATH"), help="Path to spoilers.json")
    parser.add_argument("--limit-per-source", type=int, default=DEFAULT_ITEM_LIMIT, help="Max items per source")
    parser.add_argument("--max-per-day", type=int, default=DEFAULT_MAX_PER_DAY, help="Max generated spoilers per day")
    parser.add_argument("--dry-run", action="store_true", help="Do not write files")
    return parser.parse_args()


def log(message: str) -> None:
    print(f"[info] {message}")


def warn(message: str) -> None:
    print(f"[warn] {message}", file=sys.stderr)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def today_key() -> str:
    return now_utc().strftime("%Y-%m-%d")


def resolve_output_path(explicit_output: str | None) -> Path:
    if explicit_output:
        path = Path(explicit_output)
        return path if path.is_absolute() else (ROOT_DIR / path).resolve()

    for candidate in DEFAULT_OUTPUT_CANDIDATES:
        if candidate.exists():
            return candidate

    return DEFAULT_OUTPUT_CANDIDATES[0]


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def fetch_url(url: str) -> bytes:
    req = request.Request(
        url,
        headers={
            "User-Agent": "SpoilersSeriesAutomation/1.0",
            "Accept": "application/json, application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
        },
    )
    with request.urlopen(req, timeout=20) as response:
        return response.read()


def path_get(payload: Any, path: list[str]) -> Any:
    value = payload
    for key in path:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
    return value


def clean_text(value: str | None, max_length: int = 240) -> str:
    if not value:
        return ""
    text = " ".join(str(value).replace("\n", " ").replace("\r", " ").split())
    return text[:max_length].strip()


def normalize_date(value: str | None) -> str:
    if not value:
        return today_key()

    trimmed = clean_text(value, 40)
    candidates = [trimmed, trimmed[:10], trimmed[:19]]
    parsers = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%a, %d %b %Y %H:%M:%S %z",
    ]
    for candidate in candidates:
        for parser in parsers:
            try:
                return datetime.strptime(candidate, parser).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return today_key()


def tokens(text: str) -> set[str]:
    return {token.lower() for token in WORD_RE.findall(text)}


def similarity_score(a: str, b: str) -> float:
    a_tokens = tokens(a)
    b_tokens = tokens(b)
    if not a_tokens or not b_tokens:
        return 0.0
    intersection = len(a_tokens & b_tokens)
    union = len(a_tokens | b_tokens)
    return intersection / union if union else 0.0


def find_xml_text(item: ET.Element, tags: list[str]) -> str:
    for tag in tags:
        element = item.find(tag)
        if element is not None and element.text:
            return element.text
    return ""


def atom_link(item: ET.Element) -> str:
    for link in item.findall("{http://www.w3.org/2005/Atom}link"):
        href = link.attrib.get("href")
        if href:
            return href
    return ""


def ensure_allowed_source(source: dict[str, Any]) -> bool:
    source_type = source.get("source_type")
    legal_status = source.get("legal_status")

    if source_type not in ALLOWED_SOURCE_TYPES:
        warn(f"source rejected: {source.get('id')} (unsupported source_type)")
        return False

    if legal_status != "allowed":
        warn(f"source rejected: {source.get('id')} (legal_status={legal_status})")
        return False

    return True


def make_record(source: dict[str, Any], link: str, date: str, facts: list[str]) -> FactRecord | None:
    normalized_facts = [clean_text(fact, 180) for fact in facts if clean_text(fact, 180)]
    if len(normalized_facts) < MIN_FACTS_REQUIRED:
        return None

    return FactRecord(
        source_id=source["id"],
        source_name=source["name"],
        source_link=link,
        series_id=source["series_id"],
        category=source.get("category", "Spoiler"),
        date=date,
        source_type=source["source_type"],
        facts=normalized_facts[:4],
    )


def load_rss_items(source: dict[str, Any], limit: int) -> list[FactRecord]:
    data = fetch_url(source["url"])
    root = ET.fromstring(data)
    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    records: list[FactRecord] = []

    for item in items[:limit]:
        title = clean_text(find_xml_text(item, ["title", "{http://www.w3.org/2005/Atom}title"]))
        summary = clean_text(find_xml_text(item, ["description", "summary", "{http://www.w3.org/2005/Atom}summary"]))
        link = clean_text(find_xml_text(item, ["link"])) or atom_link(item) or source["url"]
        date = normalize_date(find_xml_text(item, ["pubDate", "updated", "{http://www.w3.org/2005/Atom}updated"]))
        record = make_record(source, link, date, [title, summary])
        if record:
            records.append(record)
    return records


def load_api_items(source: dict[str, Any], limit: int) -> list[FactRecord]:
    payload = json.loads(fetch_url(source["url"]).decode("utf-8"))
    items = path_get(payload, source.get("items_path", []))
    if not isinstance(items, list):
        return []

    records: list[FactRecord] = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        title = clean_text(item.get(source.get("title_field", "title")))
        summary = clean_text(item.get(source.get("summary_field", "summary")))
        link = clean_text(item.get(source.get("link_field", "url"))) or source["url"]
        date = normalize_date(item.get(source.get("date_field", "published_at")))
        record = make_record(source, link, date, [title, summary])
        if record:
            records.append(record)
    return records


def load_manual_notes_items(source: dict[str, Any], limit: int) -> list[FactRecord]:
    notes_path = Path(source["path"])
    if not notes_path.is_absolute():
        notes_path = ROOT_DIR / notes_path
    if not notes_path.exists():
        warn(f"notes source missing: {notes_path}")
        return []

    payload = read_json(notes_path)
    items = payload.get("items", []) if isinstance(payload, dict) else []
    records: list[FactRecord] = []

    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        facts = [clean_text(value, 180) for value in item.get("facts", []) if clean_text(value, 180)]
        record = make_record(
            source,
            clean_text(item.get("internal_link")) or notes_path.as_posix(),
            normalize_date(item.get("date")),
            facts,
        )
        if record:
            records.append(record)
    return records


def load_public_press_release_items(source: dict[str, Any], limit: int) -> list[FactRecord]:
    if "rss_url" in source:
        rss_clone = dict(source)
        rss_clone["url"] = source["rss_url"]
        return load_rss_items(rss_clone, limit)
    warn(f"public_press_release source skipped: {source.get('id')} (no structured feed configured)")
    return []


def load_fact_records(sources_config: dict[str, Any], limit: int) -> list[FactRecord]:
    records: list[FactRecord] = []
    for source in sources_config.get("sources", []):
        if not source.get("enabled"):
            continue
        if not ensure_allowed_source(source):
            continue

        try:
            source_type = source["source_type"]
            if source_type == "rss":
                source_records = load_rss_items(source, limit)
            elif source_type == "api":
                source_records = load_api_items(source, limit)
            elif source_type == "manual_notes":
                source_records = load_manual_notes_items(source, limit)
            elif source_type == "public_press_release":
                source_records = load_public_press_release_items(source, limit)
            else:
                continue
            log(f"{source.get('id')} -> {len(source_records)} item(s) legalement exploitables")
            records.extend(source_records)
        except (KeyError, ValueError, ET.ParseError, error.URLError, json.JSONDecodeError) as exc:
            warn(f"source skipped: {source.get('id', 'unknown')} ({exc})")
    return records


def build_prompt(record: FactRecord) -> str:
    facts_block = "\n".join(f"- {fact}" for fact in record.facts)
    return f"""
Tu ecris pour l'application mobile "Spoilers Series FR".

Regles absolues :
- utilise uniquement les faits ci-dessous
- n'invente jamais de date, personnage, lieu ou evenement
- si les faits sont insuffisants, retourne should_publish=false
- texte entierement original
- ne copie pas, ne paraphrase pas de trop pres
- ne reprends pas la structure d'un article source
- style presse TV simple et court
- aucune mention de la source dans le texte final

Serie cible : {record.series_id}
Categorie cible : {record.category}
Date cible : {record.date}
Type de source : {record.source_type}

Faits autorises :
{facts_block}

Retourne uniquement un JSON valide :
{{
  "should_publish": true,
  "reason": "",
  "title": "titre original",
  "summary": "resume original en 1 ou 2 phrases",
  "spoiler_short": "spoiler court en une phrase",
  "content_long": "contenu long original en 2 ou 3 phrases",
  "push_notification": "notification push courte",
  "date": "{record.date}",
  "category": "{record.category}",
  "series_id": "{record.series_id}"
}}
""".strip()


def extract_output_text(body: dict[str, Any]) -> str:
    if isinstance(body.get("output_text"), str):
        return body["output_text"]
    for output in body.get("output", []):
        for content in output.get("content", []):
            if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                return content["text"]
    raise GenerationError("No output text returned by AI")


def call_openai_for_spoiler(record: FactRecord, existing_series_ids: set[str]) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise GenerationError("OPENAI_API_KEY is required")
    if record.series_id not in existing_series_ids:
        raise GenerationError(f"Unknown series_id '{record.series_id}'")

    payload = {
        "model": DEFAULT_MODEL,
        "input": build_prompt(record),
        "text": {"format": {"type": "json_object"}},
    }
    req = request.Request(
        OPENAI_API_URL,
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with request.urlopen(req, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise GenerationError(f"OpenAI HTTP {exc.code}") from exc
    except error.URLError as exc:
        raise GenerationError(f"OpenAI network error: {exc.reason}") from exc

    raw_text = extract_output_text(body)
    generated = json.loads(raw_text)
    return validate_generated_spoiler(generated, record)


def validate_generated_spoiler(payload: dict[str, Any], record: FactRecord) -> dict[str, Any]:
    should_publish = bool(payload.get("should_publish", False))
    reason = clean_text(payload.get("reason"), 180)
    date = normalize_date(payload.get("date", record.date))
    category = clean_text(payload.get("category", record.category), 40) or record.category
    series_id = clean_text(payload.get("series_id", record.series_id), 60) or record.series_id

    fields = {
        "title": clean_text(payload.get("title"), 120),
        "summary": clean_text(payload.get("summary"), 220),
        "spoiler_short": clean_text(payload.get("spoiler_short"), 160),
        "content_long": clean_text(payload.get("content_long"), 420),
        "push_notification": clean_text(payload.get("push_notification"), 120),
    }

    if not should_publish:
        raise GenerationError(reason or "AI marked content as insufficient")

    if any(not value for value in fields.values()):
        raise GenerationError("AI output missing one or more editorial fields")

    for field_value in fields.values():
        if is_too_close_to_source(field_value, record.facts):
            raise GenerationError("Generated text too close to source facts")

    return {
        "id": uuid.uuid4().hex[:12],
        "title": fields["title"],
        "summary": fields["summary"],
        "spoiler_short": fields["spoiler_short"],
        "content_long": fields["content_long"],
        "push_notification": fields["push_notification"],
        "date": date,
        "category": category,
        "series_id": series_id,
        "content": fields["content_long"]
    }


def is_too_close_to_source(text: str, facts: list[str]) -> bool:
    normalized_text = clean_text(text, 500).lower()
    for fact in facts:
        normalized_fact = clean_text(fact, 220).lower()
        if normalized_fact and normalized_fact in normalized_text:
            return True
        if similarity_score(normalized_text, normalized_fact) >= 0.8:
            return True
    return False


def load_internal_log() -> dict[str, Any]:
    if INTERNAL_LOG_PATH.exists():
        return read_json(INTERNAL_LOG_PATH)
    return {"items": []}


def daily_generated_count(internal_log: dict[str, Any], day: str) -> int:
    return sum(1 for item in internal_log.get("items", []) if item.get("generated_date") == day)


def seen_source_links(internal_log: dict[str, Any]) -> set[str]:
    return {item.get("source_link", "") for item in internal_log.get("items", []) if item.get("source_link")}


def seen_facts_hashes(internal_log: dict[str, Any]) -> set[str]:
    return {item.get("facts_hash", "") for item in internal_log.get("items", []) if item.get("facts_hash")}


def seen_title_keys(output_payload: dict[str, Any]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for item in output_payload.get("spoilers", []):
        if isinstance(item, dict):
            keys.add((str(item.get("series_id", "")).lower(), clean_text(item.get("title"), 120).lower()))
    return keys


def append_internal_log(internal_log: dict[str, Any], spoiler: dict[str, Any], record: FactRecord) -> None:
    internal_log.setdefault("items", []).append(
        {
            "spoiler_id": spoiler["id"],
            "source_id": record.source_id,
            "source_name": record.source_name,
            "source_type": record.source_type,
            "source_link": record.source_link,
            "facts": record.facts,
            "facts_hash": record.facts_hash,
            "generated_title": spoiler["title"],
            "generated_summary": spoiler["summary"],
            "generated_spoiler_short": spoiler["spoiler_short"],
            "generated_push_notification": spoiler["push_notification"],
            "generated_date": today_key(),
            "logged_at": now_utc().isoformat(),
        }
    )


def validate_spoilers_payload(payload: dict[str, Any]) -> None:
    if not isinstance(payload.get("lastUpdate"), str):
        raise GenerationError("spoilers.json must contain string lastUpdate")
    if not isinstance(payload.get("series"), list) or not isinstance(payload.get("spoilers"), list):
        raise GenerationError("spoilers.json must contain series[] and spoilers[]")

    for item in payload["series"]:
        for field in ("id", "title", "description", "image"):
            if field not in item:
                raise GenerationError(f"series item missing '{field}'")

    for item in payload["spoilers"]:
        for field in ("id", "series_id", "title", "content", "date", "category"):
            if field not in item:
                raise GenerationError(f"spoiler item missing '{field}'")


def merge_spoilers(existing: dict[str, Any], generated_items: list[dict[str, Any]]) -> dict[str, Any]:
    spoilers = existing.get("spoilers", [])
    for item in generated_items:
        public_item = {
            "id": item["id"],
            "series_id": item["series_id"],
            "title": item["title"],
            "content": item["content"],
            "date": item["date"],
            "category": item["category"],
        }
        spoilers.append(public_item)

    existing["spoilers"] = sorted(spoilers, key=lambda item: item.get("date", ""), reverse=True)
    existing["lastUpdate"] = today_key()
    validate_spoilers_payload(existing)
    return existing


def select_new_records(
    records: list[FactRecord],
    internal_log: dict[str, Any],
    output_payload: dict[str, Any],
    max_per_day: int,
) -> list[FactRecord]:
    remaining = max(0, max_per_day - daily_generated_count(internal_log, today_key()))
    if remaining == 0:
        log(f"Limite quotidienne atteinte: {max_per_day} spoiler(s)")
        return []

    links = seen_source_links(internal_log)
    hashes = seen_facts_hashes(internal_log)
    title_keys = seen_title_keys(output_payload)

    selected: list[FactRecord] = []
    for record in records:
        title_hint = clean_text(record.facts[0] if record.facts else "", 120).lower()
        dedupe_title_key = (record.series_id.lower(), title_hint)
        if record.source_link and record.source_link in links:
            continue
        if record.facts_hash in hashes:
            continue
        if dedupe_title_key in title_keys:
            continue
        selected.append(record)
        links.add(record.source_link)
        hashes.add(record.facts_hash)
        if len(selected) >= remaining:
            break
    return selected


def main() -> int:
    args = parse_args()
    output_path = resolve_output_path(args.output)
    sources_config = read_json(Path(args.sources))
    output_payload = read_json(output_path)
    internal_log = load_internal_log()

    validate_spoilers_payload(output_payload)
    records = load_fact_records(sources_config, args.limit_per_source)
    if not records:
        log("Aucune source allowed n'a fourni de faits suffisants.")
        return 0

    records = select_new_records(records, internal_log, output_payload, args.max_per_day)
    if not records:
        log("Aucun nouveau contenu legal et utile a generer.")
        return 0

    existing_series_ids = {item["id"] for item in output_payload.get("series", [])}
    generated_items: list[dict[str, Any]] = []
    existing_title_keys = seen_title_keys(output_payload)

    for record in records:
        try:
            spoiler = call_openai_for_spoiler(record, existing_series_ids)
        except GenerationError as exc:
            warn(f"generation skipped for {record.source_id}: {exc}")
            continue

        title_key = (spoiler["series_id"].lower(), spoiler["title"].strip().lower())
        if title_key in existing_title_keys:
            warn(f"duplicate title skipped: {spoiler['title']}")
            continue

        generated_items.append(spoiler)
        existing_title_keys.add(title_key)
        append_internal_log(internal_log, spoiler, record)
        log(f"genere: [{spoiler['series_id']}] {spoiler['title']}")

    if not generated_items:
        log("Rien a publier apres controle legal, anti-doublon et anti-hallucination.")
        return 0

    merged = merge_spoilers(output_payload, generated_items)

    if args.dry_run:
        print(json.dumps(merged, ensure_ascii=False, indent=2))
        return 0

    write_json(output_path, merged)
    write_json(INTERNAL_LOG_PATH, internal_log)
    log(f"Fichier mis a jour: {output_path}")
    log(f"Journal interne mis a jour: {INTERNAL_LOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
