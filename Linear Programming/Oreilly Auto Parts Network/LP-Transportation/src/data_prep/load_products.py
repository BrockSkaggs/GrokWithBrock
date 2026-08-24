import pandas as pd
import sqlite3

df = pd.read_json('products.json')

with sqlite3.connect("/code/data/oreilly_network.db") as conn:
	df.to_sql('product', conn, if_exists='replace', index=False)

print(f'Loaded {len(df)} products')