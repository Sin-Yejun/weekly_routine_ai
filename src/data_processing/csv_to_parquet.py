import pandas as pd

df = pd.read_csv("data/02_processed/hdbscan_clusters.csv")
df.to_parquet("data/02_processed/hdbscan_clusters.parquet")