# Overlay uMap — Documentation

Intégration des données de la carte privée **Nihon 2026** (uMap ID 1337267) dans l'app Leaflet.

---

## Architecture

| Fichier | Rôle |
|---|---|
| `docs/umap-nihon.json` | Données GeoJSON exportées depuis uMap (11 datalayers, ~253 éléments) |
| `docs/app.js` | Chargement, rendu Leaflet, panneau de contrôle des couches |
| `docs/index.html` | Boutons `👁` et `☰ Couches` |
| `docs/styles.css` | Styles du panneau, des étiquettes, du bouton admin |
| `server.py` | Serveur HTTP local avec endpoint `/api/update-umap` |
| `code/fetch_umap.py` | Script de traitement initial des données Playwright |

---

## Groupes de couches (UMAP\_GROUPS)

| id | Libellé | UUID(s) | Actif par défaut |
|---|---|---|---|
| `transit-seoul` | Séoul · Métro | `2d4d61f3`, `7355f167` | ✓ |
| `transit-osaka` | Osaka · Métro | `dece274a` | ✓ |
| `transit-tokyo` | Tokyo · Métro | `cc5d36c5` | ✓ |
| `trains` | Trains | `ef265376` | ✓ |
| `trains-locaux` | Trains locaux | `f2879287` (LineString) | ✓ |
| `gares` | Gares | `f2879287` (Point) | ✗ |
| `lieux` | Lieux touristiques | `51086f30` | ✓ |
| `aeroports` | Aéroports | `a2641f4d` | ✓ |
| `hotels` | Hôtels | `db1d0136` | ✓ |

---

## Fonctionnalités UI

### 👁 Bouton masquer/afficher
Masque ou restaure toutes les couches uMap d'un coup, en respectant l'état des cases à cocher individuelles. Devient semi-transparent quand les données sont masquées.

### ☰ Panneau Couches
Cases à cocher par groupe + swatch couleur. S'ouvre/ferme via le bouton, se ferme en cliquant ailleurs.

### Étiquettes au zoom
Les étiquettes permanentes (noms de lieux) apparaissent automatiquement à partir du zoom **13** (niveau quartier) et se masquent en dessous. Seuil configurable via `LABEL_ZOOM` dans `app.js`.

---

## Mode admin — Mise à jour des données uMap

### Lancer le serveur

```bash
python3 /path/to/NIHON/server.py
# → http://localhost:8765/
# → http://localhost:8765/?admin  (mode admin)
```

> Ne pas utiliser `python3 -m http.server` : il ne gère pas l'endpoint `/api/update-umap`.

### Procédure de mise à jour

1. Modifier la carte sur [umap.openstreetmap.fr](https://umap.openstreetmap.fr)
2. Ouvrir `http://localhost:8765/?admin`
3. Ouvrir le panneau **☰ Couches**
4. Coller le `sessionid` dans le champ (voir ci-dessous)
5. Cliquer **↻ Mettre à jour depuis uMap**

Le serveur télécharge les 11 datalayers via l'API uMap, régénère `docs/umap-nihon.json`, et l'overlay se recharge automatiquement sans rechargement de page.

### Récupérer le sessionid uMap

1. Se connecter sur [umap.openstreetmap.fr](https://umap.openstreetmap.fr)
2. DevTools (F12) → **Application** → **Cookies** → `umap.openstreetmap.fr`
3. Copier la valeur du cookie `sessionid`

Le sessionid est mémorisé dans le `localStorage` du navigateur — il n'est à saisir qu'une seule fois par session de navigateur.

---

## Endpoint API

### `POST /api/update-umap`

**Body JSON :**
```json
{ "session": "<sessionid>" }
```

**Réponse OK :**
```json
{ "ok": true, "layers": 11, "features": 253, "errors": [] }
```

**Réponse erreur (403 — session manquante ou expirée) :**
```json
{ "ok": false, "error": "Accès refusé — renseignez votre sessionid uMap dans le panneau admin.", "details": [...] }
```
