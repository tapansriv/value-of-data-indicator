import pandas as pd
from pathlib import Path

df = pd.read_csv("../profiles_combined.csv")

print(f"Loaded {len(df)} rows")
print("\nFirst few rows:")
print(df.head(10))
print("\nDataFrame info:")
print(df.info())
