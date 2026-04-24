# Spoilers Series Automation

Ce dossier contient un systeme separe de l'app iPhone. Il sert a produire et publier automatiquement un `spoilers.json` compatible avec :

`https://spoilers-series-data.pages.dev/spoilers.json`

## But

Le pipeline fait ceci :

1. lit les sources dans `sources.json`
2. n'utilise que les sources `legal_status: allowed`
3. recupere les nouveaux elements depuis des flux RSS publics, APIs ouvertes, communiques publics structures ou notes personnelles
4. conserve uniquement des faits courts
5. envoie ces faits a une IA pour generer plusieurs sorties editoriales entierement originales
6. refuse la publication si les faits sont insuffisants ou si le texte est trop proche de la source
7. ajoute les nouveaux spoilers dans `spoilers.json`
8. verifie que le JSON reste valide
9. garde les liens sources dans `.internal_sources.json`
10. peut commit et push automatiquement avec `publish.sh`
11. peut tourner automatiquement toutes les 6 heures via GitHub Actions

## Regles legales

- utiliser uniquement des sources autorisees
- ne pas scraper des pages interdites
- ne jamais copier un article
- ne pas paraphraser de trop pres
- ne pas reutiliser logos ou images proteges
- garder les liens sources en interne uniquement

## Fichiers

- `sources.json` : liste des sources avec statut legal
- `generate_spoilers.py` : collecte, generation IA, validation JSON
- `publish.sh` : generation + git add/commit/push
- `.internal_sources.json` : journal interne genere automatiquement
- `.github/workflows/auto-publish.yml` : scheduler GitHub Actions toutes les 6 heures

## Variables d'environnement

Le script attend :

- `OPENAI_API_KEY` : cle API pour la generation
- `OPENAI_MODEL` : optionnel, par defaut `gpt-4.1-mini`
- `SPOILERS_JSON_PATH` : optionnel, chemin du `spoilers.json` cible
- `SOURCE_ITEM_LIMIT` : optionnel, nombre maximum d'elements lus par source
- `MAX_SPOILERS_PER_DAY` : optionnel, limite journaliere, par defaut `3`
- `GIT_AUTHOR_NAME` : optionnel pour les commits automatiques
- `GIT_AUTHOR_EMAIL` : optionnel pour les commits automatiques

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

Chaque source doit definir :

- `source_type`
  - `rss`
  - `api`
  - `manual_notes`
  - `public_press_release`
- `legal_status`
  - `allowed`
  - `unknown`
  - `forbidden`

Le script utilise uniquement les sources :

- `enabled: true`
- `legal_status: "allowed"`

Les sources `unknown` et `forbidden` sont refusees automatiquement.

Exemple :

```json
{
  "id": "manual-dna",
  "enabled": true,
  "name": "Notes editoriales Demain nous appartient",
  "series_id": "demain_nous_appartient",
  "source_type": "manual_notes",
  "legal_status": "allowed",
  "path": "authorized_notes/demain_nous_appartient.json",
  "category": "Spoiler"
}
```

Series prises en charge dans l'exemple :

- `demain_nous_appartient`
- `ici_tout_commence`
- `plus_belle_la_vie`
- `un_si_grand_soleil`

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
3. execution planifiee de `publish.sh` via GitHub Actions
4. push Git automatique
5. Cloudflare Pages redeploie `spoilers.json`

### GitHub Actions

Le workflow inclus tourne :

- toutes les 6 heures
- manuellement via `workflow_dispatch`

Fichier :

`/.github/workflows/auto-publish.yml`

Secret GitHub obligatoire :

- `OPENAI_API_KEY`

## Protections ajoutees

- aucune publication si aucun nouveau contenu
- deduplication par lien source interne
- deduplication par hash des faits
- deduplication par titre/serie
- limite journaliere par defaut : `3 spoilers`
- refus automatique des sources `unknown` ou `forbidden`
- refus automatique si moins de 2 faits courts exploitables
- refus automatique si l'IA dit que les faits sont insuffisants
- refus automatique si une sortie est trop proche d'un fait source
- logs d'information et d'erreur dans la sortie console

## Notes importantes

- le script ne fait pas de scraping HTML arbitraire
- il utilise uniquement la bibliotheque standard Python
- l'IA recoit des faits courts, pas un article complet
- les liens sources restent dans `.internal_sources.json`, pas dans le JSON public
- le mode 100% automatique reste sous ta responsabilite editoriale
