# Spoilers Series Automation

Ce dossier contient un systeme separe de l'app iPhone. Il sert a produire et publier automatiquement un `spoilers.json` compatible avec :

`https://spoilers-series-data.pages.dev/spoilers.json`

## But

Le pipeline fait ceci :

1. lit les sources autorisees dans `sources.json`
2. recupere les nouveaux elements depuis des RSS publics, APIs JSON autorisees ou notes personnelles
3. conserve uniquement des faits courts
4. envoie ces faits a une IA pour generer un titre et un contenu entierement originaux
5. ajoute les nouveaux spoilers dans `spoilers.json`
6. verifie que le JSON reste valide
7. garde les liens sources dans `.internal_sources.json`
8. peut commit et push automatiquement avec `publish.sh`

## Regles legales

- utiliser uniquement des sources autorisees
- ne pas scraper des pages interdites
- ne jamais copier un article
- ne pas paraphraser de trop pres
- ne pas reutiliser logos ou images proteges
- garder les liens sources en interne uniquement

## Fichiers

- `sources.json` : liste des sources autorisees
- `generate_spoilers.py` : collecte, generation IA, validation JSON
- `publish.sh` : generation + git add/commit/push
- `.internal_sources.json` : journal interne genere automatiquement

## Variables d'environnement

Le script attend :

- `OPENAI_API_KEY` : cle API pour la generation
- `OPENAI_MODEL` : optionnel, par defaut `gpt-4.1-mini`
- `SPOILERS_JSON_PATH` : optionnel, chemin du `spoilers.json` cible
- `SOURCE_ITEM_LIMIT` : optionnel, nombre maximum d'elements lus par source

## Format de sortie attendu

Le `spoilers.json` cible doit respecter ce schema :

```json
{
  "lastUpdate": "2026-04-24",
  "series": [
    {
      "id": "dna",
      "title": "Demain nous appartient",
      "description": "Description",
      "image": ""
    }
  ],
  "spoilers": [
    {
      "id": "abc123",
      "series_id": "dna",
      "title": "Titre original",
      "content": "Texte original",
      "date": "2026-04-24",
      "category": "Spoiler"
    }
  ]
}
```

## Configurer les sources

Dans `sources.json`, active seulement les sources que tu es autorise a utiliser :

- `rss` : flux RSS public
- `json` : API JSON autorisee
- `notes` : fichier local de notes editoriales

Exemple :

```json
{
  "id": "authorized-rss-dna",
  "enabled": true,
  "type": "rss",
  "name": "Flux RSS autorise",
  "url": "https://example.com/dna.rss",
  "series_id": "dna",
  "category": "Spoiler"
}
```

## Utilisation

Verifier la generation sans ecrire :

```bash
OPENAI_API_KEY=... python3 generate_spoilers.py --dry-run
```

Generer et ecrire dans le JSON cible :

```bash
OPENAI_API_KEY=... python3 generate_spoilers.py
```

Generer puis publier sur Git :

```bash
bash publish.sh
```

## Publication automatique

Le flux recommande :

1. repo GitHub dedie aux donnees
2. Cloudflare Pages connecte a ce repo
3. execution planifiee de `publish.sh` via GitHub Actions, cron local ou autre scheduler
4. push Git automatique
5. Cloudflare Pages redeploie `spoilers.json`

## Notes importantes

- le script ne fait pas de scraping HTML arbitraire
- il utilise uniquement la bibliotheque standard Python
- l'IA recoit des faits courts, pas un article complet
- les liens sources restent dans `.internal_sources.json`, pas dans le JSON public
