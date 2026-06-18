#!/usr/bin/env python3
"""Appelle le VLR server pour synchroniser les données uMap.
Fallback : téléchargement direct avec cookie anonyme si le VLR retourne trop peu de couches.
"""
import json, urllib.request, urllib.error, sys, datetime

VLR = "https://hub.studios-voa.com:1666"
PWD = "8102-slootorP"

# Cookie d'accès anonyme uMap (à renouveler si expiré)
UMAP_ANON_COOKIE = ""  # laisser vide pour utiliser le VLR uniquement

MAP_ID = 1337267
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
    "96db60c7-9452-4e3e-b86f-74c644c6e04a",  # VOLS
]


def post(url, data=None, headers=None):
    body = json.dumps(data or {}).encode()
    req = urllib.request.Request(url, data=body,
          headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def fetch_direct(cookie):
    """Téléchargement direct depuis uMap avec cookie."""
    layers = []
    for uuid in LAYER_UUIDS:
        url = f"https://umap.openstreetmap.fr/fr/datalayer/{MAP_ID}/{uuid}/"
        req = urllib.request.Request(url, headers={
            "Cookie": cookie,
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read())
            data["_uuid"] = uuid
            opts = data.get("_umap_options", {})
            n = len(data.get("features", []))
            print(f"  OK {uuid[:8]}  {opts.get('name','?')!r:30s} {n:3d} features")
            layers.append(data)
        except Exception as e:
            print(f"  ERR {uuid[:8]}: {e}")
    return layers


# 1. Auth VLR
print("Auth VLR…")
res = post(f"{VLR}/auth/login", {"password": PWD})
token = res["token"]
print(f"Token OK ({token[:16]}…)")

# 2. Sync via VLR
print("Sync uMap via VLR…")
res = post(f"{VLR}/nihon/umap-sync", headers={"Authorization": f"Bearer {token}"})
layers = res.get("layers", [])
print(f"{len(layers)} couches reçues depuis VLR")

# 3. Si le VLR ne retourne pas toutes les couches, compléter en direct
vlr_uuids = {l.get("_uuid") for l in layers}
missing = [u for u in LAYER_UUIDS if u not in vlr_uuids]
if missing and UMAP_ANON_COOKIE:
    print(f"Couches manquantes ({len(missing)}), téléchargement direct…")
    for uuid in missing:
        url = f"https://umap.openstreetmap.fr/fr/datalayer/{MAP_ID}/{uuid}/"
        req = urllib.request.Request(url, headers={
            "Cookie": UMAP_ANON_COOKIE,
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read())
            data["_uuid"] = uuid
            opts = data.get("_umap_options", {})
            n = len(data.get("features", []))
            print(f"  OK {uuid[:8]}  {opts.get('name','?')!r:30s} {n:3d} features")
            layers.append(data)
        except Exception as e:
            print(f"  ERR {uuid[:8]}: {e}")

# 4. Rapport
for l in layers:
    opts = l.get("_umap_options", {})
    uuid = l.get("_uuid", "?")
    name = opts.get("name", "?")
    n = len(l.get("features", []))
    print(f"  - {uuid[:8]}…  {name!r:40s} {n:3d} features")

# 5. Sauvegarder
output = {
    "type": "umap_export",
    "mapId": MAP_ID,
    "mapName": "Nihon 2026",
    "exportDate": datetime.datetime.utcnow().isoformat() + "Z",
    "layers": layers,
}
out_path = "/Users/tanaismusic/Documents/DEV/NIHON/docs/umap-nihon.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False)
total = sum(len(l.get("features", [])) for l in layers)
print(f"\nDONE: {len(layers)} couches, {total} elements -> umap-nihon.json")
