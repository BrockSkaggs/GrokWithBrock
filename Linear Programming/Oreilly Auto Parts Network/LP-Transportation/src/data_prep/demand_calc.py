import pandas as pd
import numpy as np
import sqlite3

from data_prep.geo_utils import haversine_vectorized


STORM_CENTER = (35.2, -85.2)
MAX_SNOWFALL = 12.0

PRODUCT_DEMAND_LIMITS = {
    'AS242': (0, 150),
    'AS240': (0, 125),
    '16024': (0, 200),
    '17228': (0, 50),
    '20': (0, 100)
}

PRODUCT_DEMAND_SNOWFALL_MULTIPLIERS = {
    'AS242': 10,
    'AS240': 8,
    '16024': 9,
    '17228': 2,
    '20': 7
}

df = pd.read_json('selected_data.json')
df.drop(columns=['curveNumber', 'pointNumber', 'pointIndex'], inplace=True)
df['store_id'] =  (df['text'].str.split(' - ').str[0].str.strip()).astype(int)
df['dist_storm'] = haversine_vectorized(df, 'lat', 'lon', STORM_CENTER[0], STORM_CENTER[1])
df['dist_storm_percentile'] = df['dist_storm'].rank(pct=True)
df['snowfall'] = MAX_SNOWFALL * (1 - df['dist_storm_percentile']) + np.random.normal(0, 1.5, len(df))
df['snowfall'] = df['snowfall'].clip(lower=0.5, upper=MAX_SNOWFALL)


snowfall_rows = []
demand_rows = []
for _, row in df.iterrows():
    store_id = str(row['store_id'])
    snowfall_rows.append((store_id, float(row['snowfall'])))

    for product, (min_demand, max_demand) in PRODUCT_DEMAND_LIMITS.items():
        demand = row['snowfall'] * PRODUCT_DEMAND_SNOWFALL_MULTIPLIERS[product] + np.random.normal(0, 15)
        demand = int(np.clip(demand, min_demand, max_demand))
        demand_rows.append((store_id, product, demand))

with sqlite3.connect("/code/data/oreilly_network.db") as conn:
    conn.execute("DELETE FROM snowfall")
    conn.execute("DELETE FROM store_product_demand")
    conn.executemany(
        "INSERT INTO snowfall (store_id, depth_in) VALUES (?, ?)",
        snowfall_rows)
    conn.executemany(
        "INSERT INTO store_product_demand (store_id, product_pn, amount) VALUES (?, ?, ?)",
        demand_rows)