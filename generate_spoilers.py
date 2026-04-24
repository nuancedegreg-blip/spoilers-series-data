import json
import hashlib
import random
from datetime import datetime
from pathlib import Path

SPOILERS_FILE = Path("spoilers.json")
INTERNAL_FILE = Path("internal_sources.json")

MAX_PER_RUN = 10

SERIES = [
    {
        "id": "demain_nous_appartient",
        "title": "Demain nous appartient",
        "characters": ["Chloé", "Alex", "Bart", "Sara", "Roxane", "Victoire", "Georges", "Aurore", "William", "Samuel"]
    },
    {
        "id": "ici_tout_commence",
        "title": "Ici tout commence",
        "characters": ["Teyssier", "Anaïs", "Hortense", "Clotilde", "Rose", "Mehdi", "Jasmine", "Lionel", "Kelly", "Eliott"]
    },
    {
        "id": "plus_belle_la_vie",
        "title": "Plus belle la vie",
        "characters": ["Thomas", "Ariane", "Barbara", "Boher", "Luna", "Mirta", "Patrick", "Jean-Paul", "Estelle", "Céline"]
    },
    {
        "id": "un_si_grand_soleil",
        "title": "Un si grand soleil",
        "characters": ["Claire", "Élisabeth", "Manu", "Johanna", "Eve", "Gary", "Florent", "Alix", "Akim", "Louis"]
    }
]

INTRIGUES = [
    "un secret familial",
    "une trahison inattendue",
    "une dispute qui pourrait dégénérer",
    "un retour qui pourrait tout bouleverser",
    "une révélation dangereuse",
    "une relation amoureuse sous tension",
    "un mensonge difficile à cacher",
    "une enquête qui pourrait viser la mauvaise personne",
    "un choix impossible",
    "un personnage qui pourrait perdre le contrôle"
]

TITLES = [
    "{series} : {character} au cœur d’un nouveau rebondissement ?",
    "{series} : un secret pourrait tout changer pour {character}",
    "{series} : les prochains épisodes s’annoncent sous tension",
    "{series} : une révélation inattendue pourrait bouleverser les fans",
    "{series} : {character} face à une décision impossible ?",
    "{series} : un retournement de situation se prépare autour de {character}"
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

def build_spoiler(serie, character):
    intrigue = random.choice(INTRIGUES)
    second_intrigue = random.choice([i for i in INTRIGUES if i != intrigue])

    title = random.choice(TITLES).format(
        series=serie["title"],
        character=character
    )

    intro = (
        f"Les prochains épisodes de {serie['title']} pourraient réserver une surprise aux fans. "
        f"{character} semble se retrouver au cœur d’une intrigue marquée par {intrigue}."
    )

    paragraph_2 = (
        f"Rien n’est confirmé officiellement, mais plusieurs éléments laissent imaginer un tournant important. "
        f"Cette piste pourrait créer des tensions entre les personnages, notamment si {second_intrigue} venait à se confirmer."
    )

    paragraph_3 = (
        "Pour les fans, cette hypothèse ouvre la porte à de nombreuses questions sur la suite. "
        "Il s’agit toutefois d’une théorie non officielle générée automatiquement, et non d’une information confirmée."
    )

    content = f"{intro}\n\n{paragraph_2}\n\n{paragraph_3}"

    short_summary = (
        f"{character} pourrait être au centre d’un nouveau rebondissement dans {serie['title']}."
    )

    return title, content, short_summary, intrigue

def main():
    data = load_json(SPOILERS_FILE, {
        "lastUpdate": "",
        "series": [],
        "spoilers": []
    })

    data["series"] = [
        {
            "id": s["id"],
            "title": s["title"],
            "description": "Feuilleton quotidien français",
            "image": ""
        }
        for s in SERIES
    ]

    internal = load_json(INTERNAL_FILE, {"items": []})
    existing_hashes = {i.get("hash") for i in internal.get("items", [])}

    created = 0
    random.shuffle(SERIES)

    for serie in SERIES:
        characters = serie["characters"][:]
        random.shuffle(characters)

        for character in characters:
            if created >= MAX_PER_RUN:
                break

            title, content, short_summary, intrigue = build_spoiler(serie, character)

            content_hash = make_hash(
                today() + serie["id"] + character + intrigue + title
            )

            if content_hash in existing_hashes:
                continue

            spoiler = {
                "id": f"auto-{today()}-{content_hash}",
                "series_id": serie["id"],
                "title": title,
                "content": content,
                "short_summary": short_summary,
                "notification_text": title + " 👀",
                "date": today(),
                "category": "Spoiler / Théorie",
                "spoiler_level": "probable",
                "source": "internal_ai",
                "is_official": False,
                "content_type": "tv_news_style_theory",
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
                "series_id": serie["id"],
                "character": character,
                "intrigue": intrigue,
                "published": True,
                "reason": "Generated TV news style theory without copying sources"
            })

            created += 1

        if created >= MAX_PER_RUN:
            break

    save_json(SPOILERS_FILE, data)
    save_json(INTERNAL_FILE, internal)

    print(f"{created} spoilers generated in TV news style.")

if __name__ == "__main__":
    main()
