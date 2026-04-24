import json
import hashlib
from datetime import datetime
from pathlib import Path

SPOILERS_FILE = Path("spoilers.json")
SOURCES_FILE = Path("sources.json")
NOTES_FILE = Path("manual_notes.json")
INTERNAL_FILE = Path("internal_sources.json")

def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def make_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

def today():
    return datetime.utcnow().strftime("%Y-%m-%d")

def build_content(series_title, facts):
    facts_text = " ".join(facts)
    title = "Une nouvelle tension pourrait tout changer"

    content = (
        f"Dans {series_title}, une nouvelle théorie de fan imagine que la situation pourrait "
        f"rapidement se compliquer. {facts_text} "
        "Ce contenu est une hypothèse non officielle générée à partir de notes internes, "
        "et ne doit pas être présenté comme une information confirmée."
    )

    return title, content

def main():
    data = load_json(SPOILERS_FILE, {
        "lastUpdate": "",
        "series": [
            {
                "id": "demain_nous_appartient",
                "title": "Demain nous appartient",
                "description": "Feuilleton quotidien français",
                "image": ""
            },
            {
                "id": "ici_tout_commence",
                "title": "Ici tout commence",
                "description": "Feuilleton quotidien français",
                "image": ""
            },
            {
                "id": "plus_belle_la_vie",
                "title": "Plus belle la vie",
                "description": "Feuilleton quotidien français",
                "image": ""
            },
            {
                "id": "un_si_grand_soleil",
                "title": "Un si grand soleil",
                "description": "Feuilleton quotidien français",
                "image": ""
            }
        ],
        "spoilers": []
    })

    notes_data = load_json(NOTES_FILE, {"notes": []})
    sources_data = load_json(SOURCES_FILE, {"sources": []})
    internal_log = load_json(INTERNAL_FILE, {"items": []})

    allowed_sources = [
        s for s in sources_data.get("sources", [])
        if s.get("legal_status") == "allowed"
    ]

    if not allowed_sources:
        print("No allowed sources. Nothing published.")
        return

    existing_hashes = {item.get("hash") for item in internal_log.get("items", [])}
    existing_today = [
        s for s in data.get("spoilers", [])
        if s.get("date") == today()
    ]

    if len(existing_today) >= 3:
        print("Daily limit reached. Nothing published.")
        return

    series_map = {s["id"]: s for s in data.get("series", [])}

    for note in notes_data.get("notes", []):
        series_id = note.get("series_id")
        facts = note.get("facts", [])
        category = note.get("category", "Théorie")

        if not series_id or not facts:
            continue

        facts_text = " | ".join(facts)
        content_hash = make_hash(series_id + facts_text)

        if content_hash in existing_hashes:
            print("Duplicate content skipped.")
            continue

        series = series_map.get(series_id)
        if not series:
            print(f"Unknown series skipped: {series_id}")
            continue

        title, content = build_content(series["title"], facts)

        new_spoiler = {
            "id": f"auto-{today()}-{content_hash}",
            "series_id": series_id,
            "title": title,
            "content": content,
            "short_summary": content[:140] + "...",
            "notification_text": title,
            "date": today(),
            "category": category,
            "spoiler_level": "soft",
            "source": "internal_ai",
            "is_official": False
        }

        data.setdefault("spoilers", []).insert(0, new_spoiler)
        data["lastUpdate"] = today()

        internal_log.setdefault("items", []).append({
            "date": today(),
            "hash": content_hash,
            "series_id": series_id,
            "facts": facts,
            "source": "manual_notes",
            "published": True,
            "reason": "Generated from allowed internal notes"
        })

        save_json(SPOILERS_FILE, data)
        save_json(INTERNAL_FILE, internal_log)

        print("New spoiler generated.")
        return

    print("No usable notes found. Nothing published.")

if __name__ == "__main__":
    main()
