#!/usr/bin/env python3
"""Convert flight trace CSV files to GeoJSON LineString features."""

import csv
import json
import os
import re

TRACES_DIR = os.path.join(os.path.dirname(__file__), "..", "traces")
OUTPUT_DIR = TRACES_DIR  # output alongside sources


def csv_to_geojson(csv_path: str) -> dict:
    """Convert a flight CSV trace to a GeoJSON FeatureCollection."""
    filename = os.path.basename(csv_path)
    route = os.path.splitext(filename)[0]  # e.g. "CDG-ICN"
    parts = re.split(r"[-_]", route)
    origin = parts[0] if len(parts) >= 1 else ""
    destination = parts[1] if len(parts) >= 2 else ""

    coordinates = []  # [lon, lat, alt_ft]
    points = []
    callsign = ""

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pos = row["Position"].strip('"').split(",")
            lat = float(pos[0])
            lon = float(pos[1])
            alt = float(row["Altitude"]) if row["Altitude"] else 0.0
            coordinates.append([lon, lat, alt])
            if not callsign and row["Callsign"]:
                callsign = row["Callsign"]
            points.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat, alt]},
                "properties": {
                    "timestamp": int(row["Timestamp"]),
                    "utc": row["UTC"],
                    "callsign": row["Callsign"],
                    "altitude_ft": float(row["Altitude"]) if row["Altitude"] else 0,
                    "speed_kts": float(row["Speed"]) if row["Speed"] else 0,
                    "direction_deg": float(row["Direction"]) if row["Direction"] else 0,
                },
            })

    track_feature = {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coordinates},
        "properties": {
            "route": route,
            "origin": origin,
            "destination": destination,
            "callsign": callsign,
            "point_count": len(coordinates),
        },
    }

    return {
        "type": "FeatureCollection",
        "features": [track_feature],
    }


def main():
    csv_files = sorted(
        f for f in os.listdir(TRACES_DIR) if f.lower().endswith(".csv")
    )
    if not csv_files:
        print("No CSV files found in", TRACES_DIR)
        return

    for name in csv_files:
        csv_path = os.path.join(TRACES_DIR, name)
        route = os.path.splitext(name)[0]
        out_path = os.path.join(OUTPUT_DIR, route + ".geojson")

        geojson = csv_to_geojson(csv_path)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(geojson, f, ensure_ascii=False, separators=(",", ":"))

        n_pts = geojson["features"][0]["properties"]["point_count"]
        print(f"  {route}.geojson  ({n_pts} points)")

    print(f"\n{len(csv_files)} fichiers GeoJSON générés dans {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
