#!/usr/bin/env python3
"""
Merge new_travel_entries.json into travel.json.
Assigns new sequential IDs, preserving chronological order.
Removes duplicates (same day/month/hour/minute already in travel.json).

Format d'une entrée NIHON (pas de champ 'url' — photos uniquement) :
{
  "id": 1,
  "lon": 135.5023,
  "lat": 34.6937,
  "day": 1,
  "month": 4,
  "hour": 10,
  "minute": 30,
  "frame": 4,
  "year": 2025
}
"""

import json
from datetime import datetime

# ── Chemins — adapter selon votre machine ────────────────────────────
TRAVEL      = '/Users/nathalie/Documents/_TOTO/NIHON/docs/travel.json'
NEW_ENTRIES = '/Users/nathalie/Documents/_TOTO/NIHON/code/new_travel_entries.json'
OUT         = '/Users/nathalie/Documents/_TOTO/NIHON/docs/travel.json'

YEAR = 2025  # Année du voyage (à mettre à jour)


def entry_dt(e):
    return datetime(e.get('year', YEAR), e['month'], e['day'], e['hour'], e['minute'])


with open(TRAVEL) as f:
    travel = json.load(f)

with open(NEW_ENTRIES) as f:
    new_entries = json.load(f)

# Build existing timestamp set
existing_keys = {
    (e['day'], e['month'], e['hour'], e['minute'])
    for e in travel
}

# Filter out duplicates
added   = []
skipped = 0
for e in new_entries:
    key = (e['day'], e['month'], e['hour'], e['minute'])
    if key in existing_keys:
        skipped += 1
    else:
        # S'assurer que l'année est définie
        if 'year' not in e:
            e['year'] = YEAR
        # Pas de champ 'url' dans NIHON (photos uniquement)
        e.pop('url', None)
        added.append(e)
        existing_keys.add(key)

print(f"Nouvelles entrées à ajouter : {len(added)}")
print(f"Doublons ignorés            : {skipped}")

# Merge and sort
merged = travel + added
merged.sort(key=entry_dt)

# Re-assign sequential IDs
for i, e in enumerate(merged):
    e['id'] = i + 1

with open(OUT, 'w') as f:
    json.dump(merged, f, separators=(',', ':'), ensure_ascii=False)

print(f"travel.json mis à jour : {len(merged)} entrées au total")
