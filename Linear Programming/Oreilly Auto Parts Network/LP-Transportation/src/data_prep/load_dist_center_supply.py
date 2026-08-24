import pandas as pd
from sqlalchemy import engine
import numpy as np

PRODUCT_SUPPLY_LIMITS = {
    '16024': (750, 5500),
    '17228': (250, 1000),
    '20': (500, 2000),
    'AS240': (1000, 4000),
    'AS242': (500, 5000),
}

def load_dist_center_supply(engine):
    rng = np.random.default_rng()
    with engine.connect() as conn:
        dist_center_df = pd.read_sql("select * from dist_center_location", conn)
        supply_rows = []
        for _, row in dist_center_df.iterrows():
            dc_id = str(row['dc_id'])
            for product, (min_supply, max_supply) in PRODUCT_SUPPLY_LIMITS.items():
                supply = int(rng.uniform(min_supply, max_supply, 1)[0])
                supply_rows.append((dc_id, product, supply))
        cursor = conn.connection.cursor()
        cursor.execute("DELETE FROM dist_center_product_supply")
        cursor.executemany( 
            "INSERT INTO dist_center_product_supply (dc_id, product_pn, amount) VALUES (?, ?, ?)",
            supply_rows
        )
        conn.connection.commit()