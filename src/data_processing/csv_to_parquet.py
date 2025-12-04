import pandas as pd

df = pd.read_csv("data/02_processed/data.csv")
df.to_parquet("data/02_processed/data.parquet")