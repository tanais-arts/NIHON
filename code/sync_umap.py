#!/usr/bin/env python3
"""Synchronise les calques uMap vers docs/umap-nihon.json via token d'édition anonyme.
Usage : UMAP_EDIT_KEY=<token> python3 code/sync_umap.py
"""
import datetime
import http.cookiejar
import json
import os
import sys
import urllib.request
from pathlib import Path

MAP_ID = 1337267
DOCS_DIR = Path(__file__).parent.parent / "docs"
JSON_PATH = DOCS_DIR / "umap-nihon.json"

LAYER_UUIDS = [
    "5dbcf34b-2144-4d8b-be8e-3ec12f6f17df",
    "2d4d61f3-3f16-490b-8830-85ef19e7e89e",
    "7355f167-f8d4-46c7-827f-c3d1ccd43995",
    "dece274a-ae6e-4ab3-ba84-c05ddbd282fa",
    "f2879287-bedd-43e0-9982-365d0550d5b9",
    "cc5d36c5-3fcd-4722-b152-c66a0486b1d6",
    "ef265376-5d64-4d31-ab61-b10560af2c46",
    "2f4a75c4-03bb-4019-ba67-49a159729e8d",
    "51086f30-2028-4097-b185-88a261ed6ad9",
    "a2641f4d-bf1a-4cb2-9924-e437c9f893da",
    "db1d0136-6111-46bc-8a7e-2b5eb341f72e",
    "96db60c7-9452-4e3e-b86f-74c644c6e04a",
]


def get_session_from_edit_key(edit_key):
    """Visite l'URL d'édition anonyme uMap pour obtenir un sessionid Django."""
    jar    = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    url    = f"https://umap.openstreetmap.fr/fr/map/anonymous-edit/{MAP_ID}:{edit_key}"
    req    = urllib.request.Request(url, headers={"User-Agent": "NIHON-SyncBot/1.0"})
    try:
        with opener.open(req, timeout=15):
            pass
    except Exception as e:
        print(f"  [warn] visite URL édition : {e}")
    for cookie in jar:
        if cookie.name == "sessionid":
            print(f"  → sessionid obtenu")
            return cookie.value
    print("  [warn] aucun sessionid reçu — tentative sans auth")
    return None


def fetch_layer(uuid, session_id):
    url     = f"https://umap.openstreetmap.fr/fr/datalayer/{MAP_ID}/{uuid}/"
    headers = {"User-Agent": "NIHON-SyncBot/1.0"}
    if session_id:
        headers["Cookie"] = f"sessionid={session_id}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    edit_key = os.environ.get("UMAP_EDIT_KEY", "z_9DgnRE9KQW_-8hepaQmcMtub8dh8lX3XEUb_K7J_c").strip()
    if not edit_key:
        print("ERREUR : variable UMAP_EDIT_KEY manquante", file=sys.stderr)
        sys.exit(1)

    print(f"[sync-umap] {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
    session_id = get_session_from_edit_key(edit_key)

    layers = []
    errors = []
    total_features = 0

    for uuid in LAYER_UUIDS:
        try:
            data = fetch_layer(uuid, session_id)
            feats = len(data.get("features", []))
            name  = data.get("_umap_options", {}).get("name", uuid[:8])
            print(f"  ✓ {name!r:50s} — {feats} éléments")
            data["_uuid"] = uuid
            layers.append(data)
            total_features += feats
        except Exception as e:
            print(f"  ✗ {uuid[:8]}… — {e}")
            errors.append(f"{uuid}: {e}")

    if not layers:
        print("ERREUR : aucune couche récupérée", file=sys.stderr)
        sys.exit(1)

    output = {
        "type": "umap_export",
        "mapId": MAP_ID,
        "exportedAt": datetime.datetime.utcnow().isoformat() + "Z",
        "layers": layers,
    }
    JSON_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ {len(layers)} couches · {total_features} éléments → {JSON_PATH}")
    if errors:
        print(f"  {len(errors)} erreur(s) : {errors}")
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())
