#!/usr/bin/env python3
"""
resize_photos.py — Génère Photos/ (2048×1365 max) et Thumbs/ (240×120 recadré centré)
depuis un dossier de photos originales.

Usage (une passe) :
    python3 resize_photos.py /chemin/vers/Sources

Usage (surveillance continue — mode tâche de fond) :
    python3 resize_photos.py /chemin/vers/Sources --watch

Avec dossier de sortie explicite :
    python3 resize_photos.py /chemin/vers/Sources --out /chemin/vers/CDN

Dépendances :
    pip install Pillow pillow-heif watchdog
    (pillow-heif optionnel mais requis pour les HEIC d'iPhone)
"""

import argparse
import os
import sys
import time
from pathlib import Path

# ── Pillow ────────────────────────────────────────────────────────────────────
try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("❌  Pillow requis : pip install Pillow")

# ── HEIC (iPhone) ─────────────────────────────────────────────────────────────
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_OK = True
except ImportError:
    HEIC_OK = False
    print("⚠  pillow-heif non installé — les HEIC seront ignorés.")
    print("   installez-le avec : pip install pillow-heif\n")

# ── Constantes ────────────────────────────────────────────────────────────────
PHOTO_MAX   = (2048, 1365)   # Photos/  — contenu dans ce rectangle, ratio conservé
THUMB_SIZE  = (240,  120)    # Thumbs/  — recadrage centré exact
QUALITY_P   = 88             # JPEG quality pour Photos/
QUALITY_T   = 82             # JPEG quality pour Thumbs/
EXTENSIONS  = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.heic', '.heif'}


# ── Algorithmes de redimensionnement ─────────────────────────────────────────

def resize_contain(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Réduit si nécessaire sans dépasser max_w × max_h, ratio conservé."""
    img = img.copy()
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    return img


def resize_cover(img: Image.Image, dw: int, dh: int) -> Image.Image:
    """Remplit exactement dw × dh par recadrage centré."""
    src_w, src_h = img.size
    scale = max(dw / src_w, dh / src_h)
    new_w = round(src_w * scale)
    new_h = round(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - dw) // 2
    top  = (new_h - dh) // 2
    return img.crop((left, top, left + dw, top + dh))


def out_filename(src: Path) -> str:
    """Renomme en .jpg (normalise HEIC, PNG, TIFF…)."""
    return src.stem + '.jpg'


# ── Traitement d'un fichier ───────────────────────────────────────────────────

def process(src: Path, photos_dir: Path, thumbs_dir: Path, force: bool = False) -> bool:
    if src.suffix.lower() not in EXTENSIONS:
        return False
    if src.suffix.lower() in {'.heic', '.heif'} and not HEIC_OK:
        print(f"  ⚠ ignoré (HEIC non supporté) : {src.name}")
        return False

    name      = out_filename(src)
    photo_out = photos_dir / name
    thumb_out = thumbs_dir / name

    if not force and photo_out.exists() and thumb_out.exists():
        return False  # déjà traité

    try:
        with Image.open(src) as img:
            img.load()
            img = ImageOps.exif_transpose(img)   # corrige l'orientation EXIF
            if img.mode not in ('RGB',):
                img = img.convert('RGB')

            resize_contain(img.copy(), *PHOTO_MAX).save(
                photo_out, 'JPEG', quality=QUALITY_P, optimize=True
            )
            resize_cover(img.copy(), *THUMB_SIZE).save(
                thumb_out, 'JPEG', quality=QUALITY_T, optimize=True
            )

        size_p = photo_out.stat().st_size // 1024
        size_t = thumb_out.stat().st_size // 1024
        print(f"  ✓  {src.name:<40}  Photos/{name} ({size_p} Ko)  Thumbs/{name} ({size_t} Ko)")
        return True

    except Exception as e:
        print(f"  ✗  {src.name} : {e}")
        return False


# ── Passe complète ────────────────────────────────────────────────────────────

def process_all(src_dir: Path, out_dir: Path, force: bool = False) -> None:
    photos_dir = out_dir / 'Photos'
    thumbs_dir = out_dir / 'Thumbs'
    photos_dir.mkdir(parents=True, exist_ok=True)
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(f for f in src_dir.iterdir() if f.is_file())
    if not files:
        print("Aucun fichier dans le dossier source.")
        return

    done = 0
    for f in files:
        if process(f, photos_dir, thumbs_dir, force):
            done += 1

    skipped = len(files) - done
    print(f"\n✅  {done} photo(s) traitée(s)" + (f"  ({skipped} ignorée(s) — déjà converties)" if skipped else ""))


# ── Mode surveillance ─────────────────────────────────────────────────────────

def watch_mode(src_dir: Path, out_dir: Path) -> None:
    try:
        from watchdog.observers import Observer
        from watchdog.events    import FileSystemEventHandler
    except ImportError:
        sys.exit("❌  watchdog requis : pip install watchdog")

    photos_dir = out_dir / 'Photos'
    thumbs_dir = out_dir / 'Thumbs'
    photos_dir.mkdir(parents=True, exist_ok=True)
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    class Handler(FileSystemEventHandler):
        def _handle(self, path: str, force: bool = False):
            src = Path(path)
            time.sleep(0.5)        # laisse le temps à l'écriture de se terminer
            if src.is_file():
                process(src, photos_dir, thumbs_dir, force)

        def on_created(self, event):
            if not event.is_directory:
                self._handle(event.src_path)

        def on_modified(self, event):
            if not event.is_directory:
                self._handle(event.src_path, force=True)

    observer = Observer()
    observer.schedule(Handler(), str(src_dir), recursive=False)
    observer.start()
    print(f"👁  Surveillance de {src_dir}")
    print(f"   Photos/ → {photos_dir}")
    print(f"   Thumbs/ → {thumbs_dir}")
    print("   (Ctrl+C pour arrêter)\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Génère Photos/ (2048px) et Thumbs/ (240×120) depuis les originaux.'
    )
    parser.add_argument('source',
        help='Dossier contenant les photos originales (Sources/)')
    parser.add_argument('--out', '-o', default=None,
        help='Dossier de sortie pour Photos/ et Thumbs/ (défaut : parent du source)')
    parser.add_argument('--watch', '-w', action='store_true',
        help='Mode surveillance : traite les nouvelles photos en temps réel')
    parser.add_argument('--force', '-f', action='store_true',
        help='Recalculer même si les fichiers de sortie existent déjà')
    args = parser.parse_args()

    src_dir = Path(args.source).expanduser().resolve()
    if not src_dir.is_dir():
        sys.exit(f"❌  Dossier introuvable : {src_dir}")

    out_dir = Path(args.out).expanduser().resolve() if args.out else src_dir.parent

    print(f"Source  : {src_dir}")
    print(f"Sortie  : {out_dir}\n")

    process_all(src_dir, out_dir, args.force)

    if args.watch:
        watch_mode(src_dir, out_dir)


if __name__ == '__main__':
    main()
