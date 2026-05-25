#!/usr/bin/env python3
"""Script pour traiter les données uMap exportées et les sauvegarder."""
import json
import os

# UUIDs des couches dans l'ordre exact de la requête Playwright
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

SRC = os.path.expanduser(
    "~/Library/Application Support/Code/User/workspaceStorage/"
    "45063f75e8d02671ab3469719d0e93fb/GitHub.copilot-chat/chat-session-resources/"
    "12d8fe0c-04bf-4a8c-abbb-1269285fc72c/"
    "toolu_bdrk_01McjD5WUbGfCm34jds9XMgX__vscode-1779651444386/content.txt"
)
DST = os.path.join(os.path.dirname(__file__), "../docs/umap-nihon.json")

with open(SRC, "r", encoding="utf-8") as f:
    raw = f.read()

# Le fichier est au format: Result: "..json string.."
# Il faut extraire la chaîne JSON et la désérialiser deux fois
if raw.startswith("Result: "):
    raw = raw[len("Result: "):]
    raw = json.loads(raw)  # premier décodage : string JSON → str

layers = json.loads(raw)

print(f"Nombre de couches: {len(layers)}")
total = 0
for i, layer in enumerate(layers):
    opts = layer.get("_umap_options", {})
    # Attacher l'UUID au niveau racine de chaque couche
    uuid = LAYER_UUIDS[i] if i < len(LAYER_UUIDS) else None
    if uuid:
        layer["_uuid"] = uuid
    name = opts.get("name", f"Couche {i+1}")
    color = opts.get("color", "?")
    count = len(layer.get("features", []))
    total += count
    layer_id = opts.get("_layerId", "?")
    print(f"  [{i+1}] {name!r:50s} | {color:15s} | {count:3d} éléments")

print(f"\nTotal: {total} éléments")

output = {
    "type": "umap_export",
    "mapId": 1337267,
    "mapName": "Nihon 2026",
    "exportDate": "2026-05-24",
    "layers": layers,
}

dst = os.path.normpath(DST)
with open(dst, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

size = os.path.getsize(dst)
print(f"\nSauvegardé: {dst}")
print(f"Taille: {size // 1024} Ko")
