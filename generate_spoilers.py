import json
import hashlib
import random
from datetime import datetime
from pathlib import Path

SPOILERS_FILE = Path("spoilers.json")
NOTES_FILE = Path("manual_notes.json")
SOURCES_FILE = Path("sources.json")
INTERNAL_FILE = Path("internal_sources.json")

SERIES = [
    {"id": "demain_nous_appartient", "title": "Demain nous appartient", "description": "Feuilleton quotidien français", "image": ""},
    {"id": "ici_tout_commence", "title": "Ici tout commence", "description": "Feuilleton quotidien français", "image": ""},
    {"id": "plus_belle_la_vie", "title": "Plus belle la vie", "description": "Feuilleton quotidien français", "image": ""},
    {"id": "un_si_grand_soleil", "title": "Un si grand soleil", "description": "Feuilleton quotidien français", "image": ""}
]

TITLES = [
    "{character} pourrait être au cœur d’un nouveau bouleversement",
    "Un secret autour de {character} pourrait tout changer",
    "Une tension inattendue pourrait éclater dans {series}",
    "{character} pourrait cacher quelque chose d’important",
    "Un retournement de situation semble se préparer"
]

ANGLES = [
    "Plusieurs indices laissent penser que la situation pourrait rapidement se compliquer.",
    "Une nouvelle hypothèse de fan imagine un tournant important dans les prochains épisodes.",
    "Le climat semble de plus en plus tendu, et certains détails pourraient prendre une importance inattendue.",
    "Une intrigue pourrait basculer si certains secrets venaient à être révélés."
]

def today():
    return datetime.utcnow().strftime("%Y-%m-%d")

def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def make_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

def build_spoiler(series_title, note):
    character = random.choice(note.get("characters", ["un personnage"]))
    facts = note.get("facts", [])
    themes = note.get("themes", [])

    title = random.choice(TITLES).format(character=character, series=series_title)
    angle = random.choice(ANGLES)

    selected_facts = ", ".join(random.sample(facts, min(len(facts), 3)))
    selected_themes = ", ".join(random.sample(themes, min(len(themes), 2)))

    content = (
        f"Dans {series_title}, {angle} "
        f"Autour de {character}, plusieurs éléments évoquent {selected_facts}. "
        f"L’intrigue pourrait prendre une direction plus intense, notamment autour des thèmes : {selected_themes}. "
        "Ce contenu est une théorie non officielle générée à partir d’indices généraux et ne doit pas être présenté comme une information confirmée."
    )

    return title, content

def main():
    data = load_json(SPOILERS_FILE, {
        "lastUpdate": "",
        "series": SERIES,
        "spoilers": []
    })

    if not data.get("series"):
        data["series"] = SERIES

    sources = load_json(SOURCES_FILE, {"sources": []})
    allowed_sources = [s for s in sources.get("sources", []) if s.get("legal_status") == "allowed"]

    if not allowed_sources:
        print("No allowed source. Nothing published.")
        return

    notes = load_json(NOTES_FILE, {"notes": []})
    internal = load_json(INTERNAL_FILE, {"items": []})

    existing_hashes = {i.get("hash") for i in internal.get("items", [])}
    today_spoilers = [s for s in data.get("spoilers", []) if s.get("date") == today()]

    if len(today_spoilers) >= 3:
        print("Daily limit reached.")
        return

    series_map = {s["id"]: s for s in data["series"]}

    random.shuffle(notes["notes"])

    for note in notes.get("notes", []):
        series_id = note.get("series_id")
        if series_id not in series_map:
            continue

        hash_text = series_id + json.dumps(note, ensure_ascii=False) + today()
        content_hash = make_hash(hash_text)

        if content_hash in existing_hashes:
            continue

        series_title = series_map[series_id]["title"]
        title, content = build_spoiler(series_title, note)

        spoiler = {
            "id": f"auto-{today()}-{content_hash}",
            "series_id": series_id,
            "title": title,
            "content": content,
            "short_summary": content[:140] + "...",
            "notification_text": title + " 👀",
            "date": today(),
            "category": note.get("category", "Théorie"),
            "spoiler_level": "probable",
            "source": "ai_from_allowed_sources",
            "is_official": False,
            "content_type": "ultra_realistic_theory",
            "image_url": "",
            "video_url": "",
            "media_source": "none",
            "media_credit": "",
            "source_urls": []
        }

        data["spoilers"].insert(0, spoiler)
        data["lastUpdate"] = today()

        internal.setdefault("items", []).append({
            "date": today(),
            "hash": content_hash,
            "series_id": series_id,
            "published": True,
            "reason": "Ultra realistic theory generated from allowed internal notes"
        })

        save_json(SPOILERS_FILE, data)
        save_json(INTERNAL_FILE, internal)

        print("Ultra realistic spoiler generated.")
        return

    print("No new spoiler generated.")

if __name__ == "__main__":
    main()
