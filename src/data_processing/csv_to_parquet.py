import pandas as pd

df = pd.read_csv("data/02_processed/hdbscan_clusters_male_lv2.csv")
df.to_parquet("data/02_processed/hdbscan_clusters_male_lv2.parquet")