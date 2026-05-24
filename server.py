#!/usr/bin/env python3
"""Serveur HTTP pour NIHON : fichiers statiques + endpoint de mise à jour uMap."""

import datetime
import http.server
import json
import socketserver
import urllib.error
import urllib.request
from pathlib import Path

DOCS_DIR  = Path(__file__).parent / "docs"
MAP_ID    = 1337267
JSON_PATH = DOCS_DIR / "umap-nihon.json"
PORT      = 8765

# UUIDs des datalayers uMap (carte Nihon 2026)
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
]


def fetch_umap_layers(session_id=None):
    """Télécharge chaque datalayer depuis l'API uMap et retourne (layers, errors)."""
    layers = []
    errors = []
    for uuid in LAYER_UUIDS:
        url = f"https://umap.openstreetmap.fr/fr/datalayer/{MAP_ID}/{uuid}/"
        try:
            headers = {
                "User-Agent": "NIHON-App/1.0",
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            }
            if session_id:
                headers["Cookie"] = f"sessionid={session_id}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read().decode("utf-8"))
            data["_uuid"] = uuid
            layers.append(data)
            count = len(data.get("features", []))
            opts  = data.get("_umap_options", {})
            print(f"  ✓ {uuid[:8]}… {opts.get('name', '?')!r:40s} {count:3d} éléments")
        except urllib.error.HTTPError as e:
            msg = f"{uuid[:8]}: HTTP {e.code}"
            errors.append(msg)
            print(f"  ✗ {msg}")
        except Exception as e:
            msg = f"{uuid[:8]}: {e}"
            errors.append(msg)
            print(f"  ✗ {msg}")
    return layers, errors


class NihonHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCS_DIR), **kwargs)

    def do_GET(self):
        if self.path.split("?")[0] == "/api/update-umap":
            self.handle_update_umap(session_id=None)
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] == "/api/update-umap":
            length = int(self.headers.get("Content-Length", 0))
            body = {}
            if length:
                try:
                    body = json.loads(self.rfile.read(length).decode("utf-8"))
                except Exception:
                    pass
            self.handle_update_umap(session_id=body.get("session"))
        else:
            self.send_response(405)
            self.end_headers()

    def handle_update_umap(self, session_id=None):
        print(f"\n[update-umap] {datetime.datetime.now().strftime('%H:%M:%S')} "
              f"— {'avec session' if session_id else 'sans auth'}…")
        try:
            layers, errors = fetch_umap_layers(session_id=session_id)
            if not layers:
                self.send_json(403 if all("HTTP 403" in e for e in errors) else 500, {
                    "ok": False,
                    "error": "Accès refusé — renseignez votre sessionid uMap dans le panneau admin."
                             if all("HTTP 403" in e for e in errors)
                             else "Aucune couche téléchargée",
                    "details": errors,
                })
                return

            output = {
                "type": "umap_export",
                "mapId": MAP_ID,
                "mapName": "Nihon 2026",
                "exportDate": datetime.datetime.utcnow().isoformat() + "Z",
                "layers": layers,
            }
            with open(JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False)

            total = sum(len(l.get("features", [])) for l in layers)
            print(f"[update-umap] ✓ {len(layers)} couches, {total} éléments → {JSON_PATH.name}")
            self.send_json(200, {
                "ok": True,
                "layers": len(layers),
                "features": total,
                "errors": errors,
            })
        except Exception as e:
            print(f"[update-umap] ✗ {e}")
            self.send_json(500, {"ok": False, "error": str(e)})

    def send_json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Silencer les 200/304 pour ne pas polluer la console
        if args and len(args) > 1 and str(args[1]) not in ("200", "304"):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), NihonHandler) as httpd:
        httpd.allow_reuse_address = True
        print(f"[NIHON] Serveur → http://localhost:{PORT}/")
        print(f"[NIHON] Admin   → http://localhost:{PORT}/?admin")
        print(f"[NIHON] API     → http://localhost:{PORT}/api/update-umap")
        httpd.serve_forever()
