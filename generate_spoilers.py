import json
import os
import re
import hashlib
from datetime import datetime
from pathlib import Path

import feedparser
from openai import OpenAI

SPOILERS_FILE = Path("spoilers.json")
SOURCES_FILE = Path("sources.json")
INTERNAL_FILE = Path("internal_sources.json")

MAX_PER_RUN = 8
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

SERIES = [
    {"id": "demain_nous_appartient", "title": "Demain nous appartient", "description": "Spoilers, actus et théories autour de la série.", "image": ""},
    {"id": "ici_tout_commence", "title": "Ici tout commence", "description": "Spoilers, actus et théories autour de la série.", "image": ""},
    {"id": "plus_belle_la_vie", "title": "Plus belle la vie", "description": "Spoilers, actus et théories autour de la série.", "image": ""},
    {"id": "un_si_grand_soleil", "title": "Un si grand soleil", "description": "Spoilers, actus et théories autour de la série.", "image": ""}
]

def today():
    return datetime.utcnow().strftime("%Y-%m-%d")

def now_iso():
    return datetime.utcnow().isoformat() + "Z"

def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:500]

def make_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

def collect_rss_items():
    sources = load_json(SOURCES_FILE, {"sources": []}).get("sources", [])
    items = []

    for source in sources:
        if source.get("legal_status") != "allowed":
            continue
        if source.get("source_type") != "rss":
            continue

        feed = feedparser.parse(source["url"])

        for entry in feed.entries[:6]:
            title = clean(entry.get("title", ""))
            summary = clean(entry.get("summary", ""))
            link = entry.get("link", source["url"])

            if not title:
                continue

            items.append({
                "series_id": source["related_series_id"],
                "source_name": source["name"],
                "source_url": link,
                "facts": [title, summary]
            })

    return items

def ai_generate(series_title, facts):
    api_key = os.getenv("OPENAI_API_KEY")

    prompt = f"""
Tu écris pour une app française de spoilers et d'actus séries.

Série : {series_title}

Faits courts issus de flux RSS publics :
{json.dumps(facts, ensure_ascii=False)}

Objectif :
Créer un contenu original, style média TV populaire, accrocheur et crédible.

Règles :
- Ne copie aucune phrase.
- Ne paraphrase pas les articles.
- Utilise seulement les faits généraux.
- Ne présente jamais une théorie comme une certitude.
- Fais 2 ou 3 petits paragraphes.
- Le ton doit ressembler à une actu TV moderne.
- Mentionne que c’est une hypothèse si ce n’est pas confirmé.
- Pas de fausse information officielle.

Réponds uniquement en JSON valide :
{{
  "title": "...",
  "content": "...",
  "short_summary": "...",
  "notification_text": "...",
  "category": "Spoiler / Actu",
  "spoiler_level": "probable",
  "content_type": "rss_inspired_tv_news",
  "is_official": false
}}
"""

    if not api_key:
        title = f"{series_title} : les prochains épisodes s’annoncent sous tension"
        content = (
            f"Les dernières tendances autour de {series_title} laissent imaginer une suite mouvementée.\n\n"
            "Plusieurs éléments publics semblent annoncer de nouvelles tensions, mais rien n’est présenté ici comme une information officielle.\n\n"
            "Ce contenu est une analyse originale générée à partir de faits courts issus de flux publics."
        )
        return {
            "title": title,
            "content": content,
            "short_summary": content[:140] + "...",
            "notification_text": title + " 👀",
            "category": "Spoiler / Actu",
            "spoiler_level": "probable",
            "content_type": "rss_inspired_tv_news",
            "is_official": False
        }

    client = OpenAI(api_key=api_key)
    result = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "Tu es un rédacteur TV prudent, original, clair et accrocheur."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.9
    )

    text = result.choices[0].message.content.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)

def main():
    data = load_json(SPOILERS_FILE, {
        "lastUpdate": "",
        "series": SERIES,
        "spoilers": []
    })

    data["series"] = SERIES

    internal = load_json(INTERNAL_FILE, {"items": []})
    existing_hashes = {item.get("hash") for item in internal.get("items", [])}

    series_map = {s["id"]: s for s in SERIES}
    rss_items = collect_rss_items()

    created = 0

    for item in rss_items:
        if created >= MAX_PER_RUN:
            break

        series_id = item["series_id"]
        if series_id not in series_map:
            continue

        base_hash = make_hash(series_id + " ".join(item["facts"]) + item["source_url"])

        if base_hash in existing_hashes:
            continue

        series_title = series_map[series_id]["title"]

        try:
            generated = ai_generate(series_title, item["facts"])
        except Exception as e:
            print(f"AI error: {e}")
            continue

        spoiler = {
            "id": f"auto-{today()}-{base_hash}",
            "series_id": series_id,
            "title": generated.get("title", ""),
            "content": generated.get("content", ""),
            "short_summary": generated.get("short_summary", ""),
            "notification_text": generated.get("notification_text", ""),
            "date": today(),
            "published_at": now_iso(),
            "category": generated.get("category", "Spoiler / Actu"),
            "spoiler_level": generated.get("spoiler_level", "probable"),
            "source": "ai_from_rss_allowed_sources",
            "is_official": bool(generated.get("is_official", False)),
            "content_type": generated.get("content_type", "rss_inspired_tv_news"),
            "image_url": "",
            "video_url": "",
            "media_source": "none",
            "media_credit": "",
            "source_urls": [item["source_url"]]
        }

        if not spoiler["title"] or not spoiler["content"]:
            continue

        data.setdefault("spoilers", []).insert(0, spoiler)
        data["lastUpdate"] = today()

        internal.setdefault("items", []).append({
            "date": today(),
            "hash": base_hash,
            "series_id": series_id,
            "source_name": item["source_name"],
            "source_url": item["source_url"],
            "facts": item["facts"],
            "published": True,
            "reason": "Generated from allowed RSS facts without copying"
        })

        created += 1

    data["spoilers"] = sorted(
        data.get("spoilers", []),
        key=lambda x: x.get("published_at", x.get("date", "")),
        reverse=True
    )

    save_json(SPOILERS_FILE, data)
    save_json(INTERNAL_FILE, internal)

    print(f"{created} new spoilers generated.")

if __name__ == "__main__":
    main()
