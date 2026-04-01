#!/usr/bin/env python3
"""
process_photos_ci.py — Tournant dans GitHub Actions.

Variables d'environnement (définies dans le workflow) :
  PCLOUD_TOKEN  — token d'accès pCloud (secret)
  PCLOUD_BASE   — https://eapi.pcloud.com  (Europe) ou https://api.pcloud.com (USA)
  PCLOUD_ROOT   — chemin racine dans pCloud, ex: /NIHON
  CDN_BASE      — URL publique racine, ex: https://filedn.com/xxx/NIHON
  SUBFOLDER     — sous-dossier optionnel pour ce lot (ex: 01-Tokyo)

Ce script :
  1. Liste les fichiers dans pCloud PCLOUD_ROOT/Sources/[SUBFOLDER]
  2. Pour chaque fichier pas encore dans photos.json :
     - Télécharge l'original
     - Redimensionne en 2048×1365 max → upload Photos/
     - Recadre en 240×120 → upload Thumbs/
     - Lit la date EXIF → match sur travel.json
  3. Met à jour docs/photos.json (ajout + tri par date)
"""

import io
import json
import os
import re
import sys
from calendar import timegm
from datetime import datetime
from pathlib import Path

import requests
from PIL import Image, ImageOps

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_OK = True
except ImportError:
    HEIC_OK = False
    print("⚠  pillow-heif non disponible — les HEIC seront ignorés.")

# ── Config depuis l'environnement ─────────────────────────────────────────────
PCLOUD_TOKEN = os.environ['PCLOUD_TOKEN']
PCLOUD_BASE  = os.environ.get('PCLOUD_BASE', 'https://eapi.pcloud.com').rstrip('/')
PCLOUD_ROOT  = os.environ.get('PCLOUD_ROOT', '/NIHON').rstrip('/')
CDN_BASE     = os.environ.get('CDN_BASE',    'https://filedn.com/lkWW0YSMhAbFD13RbGDalo0/NIHON').rstrip('/')
SUBFOLDER    = os.environ.get('SUBFOLDER',   '').strip()

PHOTO_MAX  = (2048, 1365)
THUMB_SIZE = (240, 120)
REPO_ROOT  = Path(__file__).parent.parent


# ── pCloud API ────────────────────────────────────────────────────────────────

def pcloud_get(endpoint, **params):
    params['access_token'] = PCLOUD_TOKEN
    r = requests.get(f"{PCLOUD_BASE}/{endpoint}", params=params, timeout=60)
    r.raise_for_status()
    j = r.json()
    if j.get('result', 0) != 0:
        raise RuntimeError(f"pCloud /{endpoint}: {j.get('error')} (code {j['result']})")
    return j


def pcloud_ensure_folder(path):
    j = pcloud_get('createfolderifnotexists', path=path)
    return j['metadata']['folderid']


def pcloud_list_folder(path):
    j = pcloud_get('listfolder', path=path)
    return [f for f in j['metadata']['contents'] if not f.get('isfolder')]


def pcloud_download(file_id):
    j = pcloud_get('getfilelink', fileid=file_id)
    host = j['hosts'][0]
    r = requests.get(f"https://{host}{j['path']}", timeout=120)
    r.raise_for_status()
    return r.content


def pcloud_upload(folder_id, filename, data: bytes):
    r = requests.post(
        f"{PCLOUD_BASE}/uploadfile",
        data={'folderid': folder_id, 'filename': filename, 'access_token': PCLOUD_TOKEN},
        files={'file': (filename, data)},
        timeout=120,
    )
    j = r.json()
    if j.get('result', 0) != 0:
        raise RuntimeError(f"upload {filename}: {j.get('error')}")


# ── Image helpers ─────────────────────────────────────────────────────────────

def jpg_name(name):
    return re.sub(r'\.(heic|heif|png|tiff?)$', '.jpg', name, flags=re.IGNORECASE)


def resize_contain(img, max_w, max_h):
    out = img.copy()
    out.thumbnail((max_w, max_h), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, 'JPEG', quality=88, optimize=True)
    return buf.getvalue()


def resize_cover(img, dw, dh):
    src_w, src_h = img.size
    scale = max(dw / src_w, dh / src_h)
    out = img.resize((round(src_w * scale), round(src_h * scale)), Image.LANCZOS)
    left = (out.width - dw) // 2
    top  = (out.height - dh) // 2
    out  = out.crop((left, top, left + dw, top + dh))
    buf  = io.BytesIO()
    out.save(buf, 'JPEG', quality=82, optimize=True)
    return buf.getvalue()


def get_exif_datetime(img):
    """Lit DateTimeOriginal depuis l'EXIF — retourne datetime ou None."""
    try:
        exif = img.getexif()
        for tag_id in (36867, 36868, 306):   # DateTimeOriginal, DateTimeDigitized, DateTime
            val = exif.get(tag_id)
            if val:
                return datetime.strptime(val.strip(), '%Y:%m:%d %H:%M:%S')
    except Exception:
        pass
    return None


# ── GPS matching ─────────────────────────────────────────────────────────────

def entry_to_sec(e):
    """Convertit une entrée travel.json en secondes (face-value, sans timezone)."""
    return timegm((e['year'], e['month'], e['day'], e['hour'], e['minute'], 0))


def nearest_entry_idx(travel, photo_dt):
    if not travel or photo_dt is None:
        return 0
    photo_sec = timegm(photo_dt.timetuple())
    best, best_diff = 0, float('inf')
    for i, e in enumerate(travel):
        diff = abs(entry_to_sec(e) - photo_sec)
        if diff < best_diff:
            best_diff = diff
            best = i
    return best


# ── CDN URL ───────────────────────────────────────────────────────────────────

def cdn_url(folder, filename):
    sub = f"/{SUBFOLDER}" if SUBFOLDER else ""
    return f"{CDN_BASE}/{folder}{sub}/{filename}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    sub_label = f"/{SUBFOLDER}" if SUBFOLDER else ""
    src_path    = f"{PCLOUD_ROOT}/Sources{sub_label}"
    photos_path = f"{PCLOUD_ROOT}/Photos{sub_label}"
    thumbs_path = f"{PCLOUD_ROOT}/Thumbs{sub_label}"

    print(f"Source  pCloud : {src_path}")
    print(f"Photos  pCloud : {photos_path}")
    print(f"Thumbs  pCloud : {thumbs_path}\n")

    # Dossiers de sortie
    photos_fid = pcloud_ensure_folder(photos_path)
    thumbs_fid = pcloud_ensure_folder(thumbs_path)

    # Liste des sources
    try:
        files = pcloud_list_folder(src_path)
    except RuntimeError as e:
        print(f"❌  Impossible de lister {src_path} : {e}")
        sys.exit(1)

    print(f"{len(files)} fichier(s) source trouvé(s)\n")

    # Données existantes
    travel_path = REPO_ROOT / 'docs' / 'travel.json'
    photos_json_path = REPO_ROOT / 'docs' / 'photos.json'

    travel = json.loads(travel_path.read_text())  if travel_path.exists()      else []
    photos = json.loads(photos_json_path.read_text()) if photos_json_path.exists() else []

    existing_srcs = {p.get('src_orig', p.get('src', '')) for p in photos}

    new_entries = []
    errors = 0

    for f in files:
        name     = f['name']
        out_name = jpg_name(name)
        src_cdn  = cdn_url('Sources', name)

        if src_cdn in existing_srcs:
            print(f"  ⟳  {name} — déjà dans photos.json, ignoré")
            continue

        if name.lower().endswith(('.heic', '.heif')) and not HEIC_OK:
            print(f"  ⚠  {name} — HEIC non supporté, ignoré")
            errors += 1
            continue

        print(f"  ⚙  {name}…", end=' ', flush=True)
        try:
            data = pcloud_download(f['fileid'])
            img  = Image.open(io.BytesIO(data))
            img  = ImageOps.exif_transpose(img)
            if img.mode != 'RGB':
                img  = img.convert('RGB')

            photo_bytes = resize_contain(img, *PHOTO_MAX)
            thumb_bytes = resize_cover(img,  *THUMB_SIZE)

            pcloud_upload(photos_fid, out_name, photo_bytes)
            pcloud_upload(thumbs_fid, out_name, thumb_bytes)

            photo_dt  = get_exif_datetime(img)
            entry_idx = nearest_entry_idx(travel, photo_dt)
            caption   = photo_dt.strftime('%Y-%m-%d') if photo_dt else ''

            new_entries.append({
                'src':      cdn_url('Photos',  out_name),
                'thumb':    cdn_url('Thumbs',  out_name),
                'src_orig': src_cdn,
                'entryIdx': entry_idx,
                'caption':  caption,
            })
            print('✓')

        except Exception as e:
            print(f'✗  {e}')
            errors += 1

    # Mise à jour photos.json
    if new_entries:
        photos.extend(new_entries)
        photos.sort(key=lambda p: p.get('caption', ''))
        photos_json_path.write_text(
            json.dumps(photos, indent=2, ensure_ascii=False) + '\n'
        )
        print(f"\n✅  {len(new_entries)} nouvelle(s) photo(s) ajoutée(s) à photos.json")
    else:
        print("\nAucune nouvelle entrée.")

    if errors:
        print(f"⚠   {errors} erreur(s) — voir les logs ci-dessus.")
        sys.exit(1)


if __name__ == '__main__':
    main()
