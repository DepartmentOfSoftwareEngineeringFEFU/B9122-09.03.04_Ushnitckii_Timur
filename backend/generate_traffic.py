import numpy as np
import pandas as pd
import json
import os
from collections import defaultdict
from app.config import USE_DATABASE, DATA_DIR, HISTORICAL_DATA_FILE

def generate_traffic():
    print("🚀 Генерация плотности трафика...")

    if USE_DATABASE:
        # PostgreSQL режим
        from sqlalchemy import create_engine, text
        engine = create_engine("postgresql+psycopg2://vkr_user:vkr_password@localhost:5433/vkr_db")
        query = text("""
            SELECT mmsi, EXTRACT(HOUR FROM timestamp) as hour,
                   ST_Y(location::geometry) as lat, ST_X(location::geometry) as lon, sog
            FROM ais_records
        """)
        with engine.connect() as conn:
            rows = conn.execute(query).fetchall()
        data = [{'mmsi': r[0], 'hour': int(r[1]), 'lat': r[2], 'lon': r[3], 'sog': r[4] if r[4] else 0} for r in rows]
    else:
        # Файловый режим: читаем Parquet
        if not os.path.exists(HISTORICAL_DATA_FILE):
            print(f"❌ Файл {HISTORICAL_DATA_FILE} не найден!")
            return
        df = pd.read_parquet(HISTORICAL_DATA_FILE)
        if 'timestamp' not in df.columns:
            if 'base_date_time' in df.columns:
                df['timestamp'] = pd.to_datetime(df['base_date_time'])
            else:
                print("❌ Нет колонки timestamp или base_date_time!")
                return
        if 'mmsi' not in df.columns:
            df['mmsi'] = df.index  # временный идентификатор
        df = df.rename(columns={'latitude': 'lat', 'longitude': 'lon'})
        df['hour'] = df['timestamp'].dt.hour
        data = df[['mmsi', 'hour', 'lat', 'lon', 'sog']].to_dict('records')

    print(f"✅ Загружено {len(data)} записей")

    cell_size = 0.2
    traffic_data = defaultdict(lambda: {'vessels': set(), 'speeds': []})

    for row in data:
        cell_lat = round(row['lat'] / cell_size) * cell_size
        cell_lon = round(row['lon'] / cell_size) * cell_size
        cell_key = (cell_lat, cell_lon, row['hour'])

        traffic_data[cell_key]['vessels'].add(row['mmsi'])
        if row.get('sog'):
            traffic_data[cell_key]['speeds'].append(row['sog'])

    traffic_records = []
    for (lat, lon, hour), d in traffic_data.items():
        if len(d['vessels']) >= 3:
            traffic_records.append({
                'lat': lat, 'lon': lon, 'hour': hour,
                'vessel_count': len(d['vessels']),
                'avg_speed': np.mean(d['speeds']) if d['speeds'] else 15.0
            })

    print(f"✅ Найдено {len(traffic_records)} точек трафика")

    if USE_DATABASE:
        from sqlalchemy import create_engine, text
        engine = create_engine("postgresql+psycopg2://vkr_user:vkr_password@localhost:5433/vkr_db")
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM traffic_density"))
            for r in traffic_records:
                conn.execute(text("""
                    INSERT INTO traffic_density (center, hour_of_day, vessel_count, avg_speed)
                    VALUES (ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :hour, :count, :speed)
                """), {'lat': r['lat'], 'lon': r['lon'], 'hour': r['hour'], 'count': r['vessel_count'],
                       'speed': r['avg_speed']})
            conn.commit()
        print("🎉 Трафик сохранён в БД!")
    else:
        os.makedirs(DATA_DIR, exist_ok=True)
        output_file = os.path.join(DATA_DIR, "traffic_density.json")
        json_data = []
        for r in traffic_records:
            json_data.append({
                "lat": r['lat'],
                "lon": r['lon'],
                "hour": r['hour'],
                "intensity": r['vessel_count'],
                "avg_speed": r['avg_speed']
            })
        with open(output_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        print(f"🎉 Трафик сохранён в {output_file}")

if __name__ == "__main__":
    generate_traffic()