import pandas as pd
from pathlib import Path

parquet_file = Path(__file__).parent.parent / "data" / "synthetic_ais.parquet"
df = pd.read_parquet(parquet_file)

print(f"📊 Всего записей: {len(df)}")
print(f"\n📋 Названия колонок ({len(df.columns)} шт.):")
for i, col in enumerate(df.columns):
    print(f"  {i+1}. {col} (тип: {df[col].dtype})")

print(f"\n🔍 Первые 3 строки:")
print(df.head(3))