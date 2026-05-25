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
| `transit` | Métro / Tram | `2d4d61f3`, `7355f167` (Séoul), `dece274a` (Osaka), `cc5d36c5` (Tokyo), `f2879287` (Kyoto) | ✓ |
| `trains` | Trains | `ef265376` | ✓ |
| `vols` | Vols | `96db60c7` | ✓ |
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

Le sessionid est un cookie de session déposé par uMap quand tu es connecté·e avec ton compte OpenStreetMap. Il expire quand tu te déconnectes ou après une période d'inactivité.

#### Chrome / Brave / Edge

1. Aller sur **[umap.openstreetmap.fr](https://umap.openstreetmap.fr)** et se connecter
2. Ouvrir les DevTools : `⌘ Cmd + Option + I` (Mac) ou `F12`
3. Onglet **Application** (dans la barre supérieure des DevTools)
4. Dans le panneau gauche : **Storage → Cookies → https://umap.openstreetmap.fr**
5. Repérer la ligne dont le **Name** est `sessionid`
6. Cliquer dessus → copier la colonne **Value**

```
Exemple de valeur : abc123xyz456def789...  (longue chaîne alphanumérique)
```

#### Firefox

1. Aller sur **[umap.openstreetmap.fr](https://umap.openstreetmap.fr)** et se connecter
2. Ouvrir les DevTools : `⌘ Cmd + Option + I` ou `F12`
3. Onglet **Stockage**
4. Dans le panneau gauche : **Cookies → https://umap.openstreetmap.fr**
5. Repérer `sessionid` et copier sa valeur

#### Safari

1. Activer les outils de développement si nécessaire : **Safari → Réglages → Avancé → Afficher les outils de développement**
2. Aller sur **[umap.openstreetmap.fr](https://umap.openstreetmap.fr)** et se connecter
3. Menu **Développement → Afficher l'inspecteur web**
4. Onglet **Stockage → Cookies → umap.openstreetmap.fr**
5. Repérer `sessionid` et copier sa valeur

---

#### Coller le sessionid dans l'app

1. Ouvrir `http://localhost:8765/?admin`
2. Cliquer sur **☰ Couches** pour ouvrir le panneau
3. Coller la valeur dans le champ **`sessionid (cookie uMap)`** en bas du panneau
4. La valeur est automatiquement sauvegardée dans le `localStorage` — **elle est mémorisée d'une session à l'autre** dans ce navigateur, pas besoin de la resaisir sauf si le cookie uMap a expiré

> **Note :** si la mise à jour retourne une erreur "Accès refusé", le sessionid a expiré → se reconnecter sur uMap et récupérer un nouveau sessionid.

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
