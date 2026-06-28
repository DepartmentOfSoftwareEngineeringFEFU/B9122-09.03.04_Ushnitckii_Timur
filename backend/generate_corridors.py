import numpy as np
import pandas as pd
import json
import os
from collections import defaultdict
from app.config import USE_DATABASE, DATA_DIR, HISTORICAL_DATA_FILE

def generate_corridors():
    print("🚀 Генерация морских коридоров...")

    # 1. Загрузка данных
    if USE_DATABASE:
        # PostgreSQL режим
        from sqlalchemy import create_engine, text
        engine = create_engine("postgresql+psycopg2://vkr_user:vkr_password@localhost:5433/vkr_db")
        query = text("""
            SELECT mmsi, ST_Y(location::geometry) as lat, ST_X(location::geometry) as lon, sog
            FROM ais_records
        """)
        with engine.connect() as conn:
            rows = conn.execute(query).fetchall()
        data = [{'mmsi': r[0], 'lat': r[1], 'lon': r[2], 'sog': r[3]} for r in rows]
    else:
        # Файловый режим: читаем Parquet
        if not os.path.exists(HISTORICAL_DATA_FILE):
            print(f"❌ Файл {HISTORICAL_DATA_FILE} не найден!")
            return
        df = pd.read_parquet(HISTORICAL_DATA_FILE)
        if 'mmsi' not in df.columns:
            df['mmsi'] = df.index  # временный идентификатор
        df = df.rename(columns={'latitude': 'lat', 'longitude': 'lon'})
        data = df[['mmsi', 'lat', 'lon', 'sog']].to_dict('records')

    print(f"✅ Загружено {len(data)} записей")

    # 2. Агрегация по ячейкам
    cell_size = 0.2
    cell_vessels = defaultdict(set)
    cell_speeds = defaultdict(list)

    for row in data:
        cell_lat = round(row['lat'] / cell_size) * cell_size
        cell_lon = round(row['lon'] / cell_size) * cell_size
        cell_key = (cell_lat, cell_lon)

        cell_vessels[cell_key].add(row['mmsi'])
        if row.get('sog'):
            cell_speeds[cell_key].append(row['sog'])

    # 3. Формирование коридоров
    corridors = []
    for cell_key, vessels in cell_vessels.items():
        if len(vessels) >= 20:  # порог
            corridors.append({
                'lat': cell_key[0],
                'lon': cell_key[1],
                'traffic_count': len(vessels),
                'avg_speed': np.mean(cell_speeds.get(cell_key, [15]))
            })

    corridors.sort(key=lambda x: x['traffic_count'], reverse=True)
    top_corridors = corridors[:200]

    print(f"✅ Найдено {len(corridors)} коридоров (порог ≥20 судов)")
    print(f"📊 Сохраняем ТОП-200 из {len(corridors)}")

    # 4. Сохранение
    if USE_DATABASE:
        from sqlalchemy import create_engine, text
        engine = create_engine("postgresql+psycopg2://vkr_user:vkr_password@localhost:5433/vkr_db")
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM maritime_corridors"))
            for c in top_corridors:
                conn.execute(text("""
                    INSERT INTO maritime_corridors (center, width_km, traffic_count, avg_speed)
                    VALUES (ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :width, :count, :speed)
                """), {'lat': c['lat'], 'lon': c['lon'], 'width': cell_size * 111, 'count': c['traffic_count'],
                       'speed': c['avg_speed']})
            conn.commit()
        print("🎉 Коридоры сохранены в БД!")
    else:
        os.makedirs(DATA_DIR, exist_ok=True)
        output_file = os.path.join(DATA_DIR, "maritime_corridors.json")
        json_data = []
        for idx, c in enumerate(top_corridors):
            json_data.append({
                "id": idx + 1,
                "center": {"lat": c['lat'], "lon": c['lon']},
                "width_km": cell_size * 111,
                "traffic_count": c['traffic_count'],
                "avg_speed": c['avg_speed']
            })
        with open(output_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        print(f"🎉 Коридоры сохранены в {output_file}")

    print(f"📈 Максимальный трафик: {top_corridors[0]['traffic_count'] if top_corridors else 0} судов")


if __name__ == "__main__":
    generate_corridors()