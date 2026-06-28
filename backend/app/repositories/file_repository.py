"""
Репозиторий для работы с файловым хранилищем (Parquet, JSON).
Используется, когда USE_DATABASE = False.
"""
import pandas as pd
import json
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from sklearn.neighbors import KDTree
from app.config import (
    HISTORICAL_DATA_FILE, RISK_ZONES_FILE, CURRENT_VESSELS_FILE,
    TRAFFIC_DENSITY_FILE, MARITIME_CORRIDORS_FILE
)


class FileRepository:
    def __init__(self):
        self.historical_df = None
        self.risk_zones = []
        self.current_vessels = []
        self.traffic_density = []
        self.maritime_corridors = []
        self.kdtree = None
        self.coords = None
        self._load_data()

    def _load_data(self):
        """Загрузка всех данных из файлов при инициализации"""
        # Загрузка исторических данных
        try:
            self.historical_df = pd.read_parquet(HISTORICAL_DATA_FILE)
            print(f"✅ Загружено {len(self.historical_df)} исторических записей")

            # Убеждаемся, что колонка timestamp существует
            if 'timestamp' not in self.historical_df.columns:
                if 'base_date_time' in self.historical_df.columns:
                    self.historical_df['timestamp'] = pd.to_datetime(self.historical_df['base_date_time'])
                    print("✅ Добавлена колонка timestamp из base_date_time")
                else:
                    print("⚠️ Колонка timestamp не найдена, фильтрация по дате будет недоступна")
                    # Создаём фиктивный timestamp, чтобы не падать
                    self.historical_df['timestamp'] = pd.NaT
        except Exception as e:
            print(f"❌ Ошибка загрузки исторических данных: {e}")
            self.historical_df = pd.DataFrame()

        # Загрузка зон риска с преобразованием формата
        try:
            with open(RISK_ZONES_FILE, 'r') as f:
                raw_zones = json.load(f)
            self.risk_zones = []
            for idx, zone in enumerate(raw_zones):
                center = zone.get("center")
                if isinstance(center, list) and len(center) == 2:
                    self.risk_zones.append({
                        "id": zone.get("id", idx + 1),
                        "center": {"lat": float(center[0]), "lon": float(center[1])},
                        "radius_km": float(zone.get("radius_km", 0)),
                        "avg_risk_score": float(zone.get("avg_risk", 0)),
                        "points_count": zone.get("points_count", 0)
                    })
                elif isinstance(center, dict) and "lat" in center and "lon" in center:
                    self.risk_zones.append({
                        "id": zone.get("id", idx + 1),
                        "center": {"lat": float(center["lat"]), "lon": float(center["lon"])},
                        "radius_km": float(zone.get("radius_km", 0)),
                        "avg_risk_score": float(zone.get("avg_risk", 0)),
                        "points_count": zone.get("points_count", 0)
                    })
                else:
                    print(f"⚠️ Неизвестный формат зоны риска: {zone}")
            print(f"✅ Загружено {len(self.risk_zones)} зон риска")
        except FileNotFoundError:
            print(f"⚠️ Файл {RISK_ZONES_FILE} не найден, зоны риска не загружены")
        except Exception as e:
            print(f"❌ Ошибка загрузки зон риска: {e}")
            self.risk_zones = []

        # Загрузка текущих судов
        try:
            with open(CURRENT_VESSELS_FILE, 'r') as f:
                self.current_vessels = json.load(f)
            print(f"✅ Загружено {len(self.current_vessels)} текущих судов")
        except FileNotFoundError:
            print(f"⚠️ Файл {CURRENT_VESSELS_FILE} не найден, текущие суда не загружены")
        except Exception as e:
            print(f"❌ Ошибка загрузки текущих судов: {e}")
            self.current_vessels = []

        # Загрузка морских коридоров (если есть)
        try:
            with open(MARITIME_CORRIDORS_FILE, 'r') as f:
                raw_corridors = json.load(f)
            self.maritime_corridors = []
            for c in raw_corridors:
                center = c.get("center", {})
                self.maritime_corridors.append({
                    "id": c.get("id", 0),
                    "center": {"lat": float(center.get("lat", 0)), "lon": float(center.get("lon", 0))},
                    "width_km": float(c.get("width_km", 0)),
                    "traffic_count": int(c.get("traffic_count", 0)),
                    "avg_speed": float(c.get("avg_speed", 0))
                })
            print(f"✅ Загружено {len(self.maritime_corridors)} морских коридоров")
        except FileNotFoundError:
            print(f"⚠️ Файл {MARITIME_CORRIDORS_FILE} не найден, коридоры не загружены")
        except Exception as e:
            print(f"❌ Ошибка загрузки коридоров: {e}")
            self.maritime_corridors = []

        # Построение KDTree для быстрого поиска по координатам
        if not self.historical_df.empty:
            coords = self.historical_df[['latitude', 'longitude']].values
            self.coords = coords
            self.kdtree = KDTree(coords, metric='euclidean')

    def get_heatmap_data(
        self,
        source: str = "retrospective",
        grid_size: float = 0.1,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        start_hour: Optional[int] = None,
        end_hour: Optional[int] = None
    ) -> List[List]:
        if self.historical_df.empty:
            return []

        df = self.historical_df.copy()
        print(f"📊 Фильтр: start_date={start_date}, end_date={end_date}, start_hour={start_hour}, end_hour={end_hour}")

        # Фильтрация по дате
        if 'timestamp' in df.columns and not df['timestamp'].isna().all():
            if start_date:
                df = df[df['timestamp'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['timestamp'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1)]
            if start_hour is not None:
                df = df[df['timestamp'].dt.hour >= start_hour]
            if end_hour is not None:
                df = df[df['timestamp'].dt.hour <= end_hour]
        else:
            print("⚠️ Нет колонки timestamp или все значения NaN – фильтрация по времени пропущена")

        if df.empty:
            print("⚠️ После фильтрации данных не осталось")
            return []

        # Агрегация по ячейкам
        lat_round = np.round(df['latitude'] / grid_size) * grid_size
        lon_round = np.round(df['longitude'] / grid_size) * grid_size
        grouped = df.groupby([lat_round, lon_round]).agg(
            intensity=('risk_score', 'mean')
        ).reset_index()
        points = [[row[0], row[1], row[2]] for row in grouped.values]

        if points:
            max_intensity = max(p[2] for p in points)
            if max_intensity > 0:
                points = [[p[0], p[1], p[2] / max_intensity] for p in points]
        print(f"📊 Тепловая карта: {len(points)} точек")
        return points

    def get_risk_zones(self) -> List[Dict]:
        return self.risk_zones

    def get_maritime_corridors(self) -> List[Dict]:
        return self.maritime_corridors

    def get_traffic_density(
        self,
        hour: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """Агрегация плотности трафика из исторических данных"""
        if self.historical_df.empty:
            return []

        df = self.historical_df.copy()

        # Фильтрация по дате и часу
        if 'timestamp' in df.columns and not df['timestamp'].isna().all():
            if start_date:
                df = df[df['timestamp'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['timestamp'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1)]
            if hour is not None:
                df = df[df['timestamp'].dt.hour == hour]
        else:
            print("⚠️ Нет колонки timestamp – фильтрация по времени пропущена")

        if df.empty:
            return []

        # Агрегация по ячейкам 0.1° и часам
        lat_round = np.round(df['latitude'] / 0.1) * 0.1
        lon_round = np.round(df['longitude'] / 0.1) * 0.1

        # Добавим час, если есть timestamp
        if 'timestamp' in df.columns and not df['timestamp'].isna().all():
            df['hour'] = df['timestamp'].dt.hour
            grouped = df.groupby([lat_round, lon_round, 'hour']).agg(
                vessel_count=('sog', 'count'),
                avg_speed=('sog', 'mean')
            ).reset_index()
            traffic = []
            for _, row in grouped.iterrows():
                traffic.append({
                    "lat": float(row['lat_round']),
                    "lon": float(row['lon_round']),
                    "intensity": int(row['vessel_count']),
                    "hour": int(row['hour']),
                    "date": None  # дата не сохраняется в агрегации
                })
        else:
            grouped = df.groupby([lat_round, lon_round]).agg(
                vessel_count=('sog', 'count'),
                avg_speed=('sog', 'mean')
            ).reset_index()
            traffic = []
            for _, row in grouped.iterrows():
                traffic.append({
                    "lat": float(row['lat_round']),
                    "lon": float(row['lon_round']),
                    "intensity": int(row['vessel_count']),
                    "hour": None,
                    "date": None
                })
        return traffic

    def get_current_vessels(self) -> List[Dict]:
        return self.current_vessels

    def get_weather_for_point(self, lat: float, lon: float, date: Optional[str] = None) -> Dict:
        if self.historical_df.empty:
            return {"wind_speed": 0, "wave_height": 0, "risk_score": 0}

        df = self.historical_df.copy()
        if date and 'timestamp' in df.columns:
            df = df[df['timestamp'].dt.date == pd.to_datetime(date).date()]

        if df.empty:
            return {"wind_speed": 0, "wave_height": 0, "risk_score": 0}

        # Вычисляем расстояние до точки
        df['dist'] = np.sqrt((df['latitude'] - lat)**2 + (df['longitude'] - lon)**2)
        nearest = df.loc[df['dist'].idxmin()]

        return {
            "wind_speed": float(nearest.get('wind_speed', 0)),
            "wave_height": float(nearest.get('wave_height', 0)),
            "risk_score": float(nearest.get('risk_score', 0))
        }

    def predict_speed_at_point(
        self,
        lat: float,
        lon: float,
        vessel_type: str = "cargo",
        radius_km: float = 10.0
    ) -> float:
        if self.kdtree is None or self.coords is None:
            return 15.0

        radius_deg = radius_km / 111.0
        indices = self.kdtree.query_radius([[lat, lon]], r=radius_deg)[0]

        if len(indices) == 0:
            return 15.0

        speeds = self.historical_df.iloc[indices]['sog'].dropna()
        if len(speeds) == 0:
            return 15.0
        return float(speeds.mean())

    def find_similar_situations(
        self,
        risk_score: float,
        wind_speed: float,
        wave_height: float,
        vessel_type: str = "cargo",
        season: str = "summer",
        k: int = 10
    ) -> Tuple[List[Dict], Optional[Dict]]:
        if self.historical_df.empty:
            return [], None

        df = self.historical_df.copy()
        df['sim'] = np.sqrt(
            (df['risk_score'] - risk_score)**2 +
            (df['wind_speed'] - wind_speed)**2 +
            (df['wave_height'] - wave_height)**2
        )
        df = df.sort_values('sim').head(k)
        situations = df.to_dict(orient='records')

        recommended = None
        if situations:
            min_risk_idx = min(range(len(situations)), key=lambda i: situations[i]['risk_score'])
            recommended = situations[min_risk_idx]

        return situations, recommended

    def get_historical_stats(self) -> Dict:
        if self.historical_df.empty:
            return {"avg_risk": 0, "avg_wind": 0, "avg_wave": 0, "total_records": 0}
        return {
            "avg_risk": float(self.historical_df['risk_score'].mean()),
            "avg_wind": float(self.historical_df['wind_speed'].mean()),
            "avg_wave": float(self.historical_df['wave_height'].mean()),
            "total_records": int(len(self.historical_df))
        }