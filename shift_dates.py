import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def shift_to_retrospective():
    df = pd.read_parquet("data/historical_enriched.parquet")
    start = datetime(2020, 1, 1)
    end = datetime(2023, 12, 31)
    delta = (end - start).days
    def random_date():
        return start + timedelta(days=np.random.randint(0, delta))
    df['base_date_time'] = df['base_date_time'].apply(lambda x: random_date())
    df.to_parquet("data/retrospective.parquet", index=False)
    print("Ретроспективные данные сохранены в data/retrospective.parquet")

if __name__ == "__main__":
    shift_to_retrospective()
