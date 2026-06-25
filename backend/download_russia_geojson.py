import requests
import json
import os

# Источник: click_that_hood — содержит именно country boundaries
url = "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson"

print("Скачивание границ России...")
response = requests.get(url, timeout=30)

if response.status_code == 200:
    data = response.json()
    features = data.get('features', [])
    print(f"Найдено {len(features)} объектов")

    # Проверяем что это действительно Россия
    for f in features:
        name = f.get('properties', {}).get('name', 'Unknown')
        print(f"  - {name}")

    output_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'russia_border.geojson')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"Сохранено: {output_path} ({size_kb:.1f} KB)")
else:
    print(f"Ошибка: {response.status_code}")