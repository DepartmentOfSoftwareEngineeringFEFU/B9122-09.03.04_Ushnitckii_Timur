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
        try:
            self.historical_df = pd.read_parquet(HISTORICAL_DATA_FILE)
            print(f"✅ Загружено {len(self.historical_df)} исторических записей")
        except Exception as e:
            print(f"❌ Ошибка загрузки исторических данных: {e}")
            self.historical_df = pd.DataFrame()

        try:
            with open(RISK_ZONES_FILE, 'r') as f:
                self.risk_zones = json.load(f)
            print(f"✅ Загружено {len(self.risk_zones)} зон риска")
        except Exception as e:
            print(f"❌ Ошибка загрузки зон риска: {e}")
            self.risk_zones = []

        try:
            with open(CURRENT_VESSELS_FILE, 'r') as f:
                self.current_vessels = json.load(f)
            print(f"✅ Загружено {len(self.current_vessels)} текущих судов")
        except Exception as e:
            print(f"❌ Ошибка загрузки текущих судов: {e}")
            self.current_vessels = []

        # Построение KDTree для быстрого поиска по координатам
        if not self.historical_df.empty:
            coords = self.historical_df[['latitude', 'longitude']].values
            self.coords = coords
            self.kdtree = KDTree(coords, metric='euclidean')

    # --- Методы, аналогичные DatabaseRepository ---

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

        # Фильтрация по дате (если есть колонка timestamp)
        if 'timestamp' in df.columns:
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
            if start_date:
                df = df[df['date'] >= pd.to_datetime(start_date).date()]
            if end_date:
                df = df[df['date'] <= pd.to_datetime(end_date).date()]
            if start_hour is not None:
                df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
                df = df[(df['hour'] >= start_hour) & (df['hour'] <= end_hour)]

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
        # В файловом режиме возвращаем пустой список или агрегируем из historical_df
        return []

    def get_current_vessels(self) -> List[Dict]:
        return self.current_vessels

    def get_weather_for_point(self, lat: float, lon: float, date: Optional[str] = None) -> Dict:
        if self.historical_df.empty:
            return {"wind_speed": 0, "wave_height": 0, "risk_score": 0}

        # Простой поиск ближайшей записи
        df = self.historical_df.copy()
        if date:
            df['date'] = pd.to_datetime(df['timestamp']).dt.date if 'timestamp' in df.columns else None
            if 'date' in df.columns:
                df = df[df['date'] == pd.to_datetime(date).date()]

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

        # Поиск ближайших точек в радиусе (в градусах)
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
        # Упрощённый поиск – без нормализации, по евклидову расстоянию
        # В реальном проекте нужно нормализовать признаки
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