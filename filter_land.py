#!/usr/bin/env python3
"""
Фильтрация береговой линии Natural Earth 1:50m по границам Дальнего Востока.
Корректно обрабатывает долготы в диапазоне -180..180.
"""

import json
import os
from shapely.geometry import Polygon, shape
from shapely.ops import unary_union
from app.config import MIN_LAT, MAX_LAT, MIN_LON, MAX_LON

INPUT_FILE = "data/land_polygons_50m.geojson"
OUTPUT_FILE = "data/land_polygons_far_east.geojson"

def normalize_lon(lon):
    while lon > 180:
        lon -= 360
    while lon < -180:
        lon += 360
    return lon

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Файл {INPUT_FILE} не найден. Сначала загрузите береговую линию, запустив бэкенд один раз.")
        return

    print(f"Загрузка {INPUT_FILE}...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    min_lon_norm = normalize_lon(MIN_LON)
    max_lon_norm = normalize_lon(MAX_LON)
    bbox_parts = []
    if min_lon_norm <= 180:
        bbox_parts.append(Polygon([
            (min_lon_norm, MIN_LAT),
            (180, MIN_LAT),
            (180, MAX_LAT),
            (min_lon_norm, MAX_LAT),
            (min_lon_norm, MIN_LAT)
        ]))
    if max_lon_norm >= -180:
        bbox_parts.append(Polygon([
            (-180, MIN_LAT),
            (max_lon_norm, MIN_LAT),
            (max_lon_norm, MAX_LAT),
            (-180, MAX_LAT),
            (-180, MIN_LAT)
        ]))
    bbox = unary_union(bbox_parts)

    new_features = []
    total = len(data["features"])
    print(f"Обработка {total} полигонов...")
    for i, feature in enumerate(data["features"]):
        geom = shape(feature["geometry"])
        if geom.intersects(bbox):
            intersected = geom.intersection(bbox)
            if intersected.is_empty:
                continue
            new_feature = {
                "type": "Feature",
                "properties": feature["properties"],
                "geometry": intersected.__geo_interface__
            }
            new_features.append(new_feature)
        if (i+1) % 1000 == 0:
            print(f"Обработано {i+1} из {total}")

    filtered_data = {
        "type": "FeatureCollection",
        "features": new_features
    }

    print(f"Сохраняем {len(new_features)} полигонов в {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(filtered_data, f)

    print("Готово!")

if __name__ == "__main__":
    main()
