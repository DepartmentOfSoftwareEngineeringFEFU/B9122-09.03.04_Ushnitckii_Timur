# backend/services/data_loader.py
import pandas as pd
import geopandas as gpd
from fastapi import UploadFile
from sqlalchemy import create_engine
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AISDataLoader:
    def __init__(self, db_connection_string: str):
        self.engine = create_engine(db_connection_string)
    async def load_from_csv(self, file: UploadFile) -> dict:
        try:
            df = pd.read_csv(file.file)
            df = self._clean_data(df)
            gdf = gpd.GeoDataFrame(
                df,
                geometry=gpd.points_from_xy(df.longitude, df.latitude),
                crs="EPSG:4326"
            )
            gdf.to_postgis('ais_records', self.engine, if_exists='append')
            return {
                "status": "success",
                "records_loaded": len(df),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Ошибка загрузки: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df[(df.longitude.between(-180, 180)) &
                (df.latitude.between(-90, 90))]
        df = df.drop_duplicates(subset=['mmsi', 'timestamp'])
        df['speed'] = df['speed'].fillna(0)
        df['course'] = df['course'].fillna(0)
        return df