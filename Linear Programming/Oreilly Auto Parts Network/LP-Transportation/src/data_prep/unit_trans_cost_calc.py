import pandas as pd
from sqlalchemy import text, bindparam

from common import engine, STATE_SUBSET
from data_prep.geo_utils import haversine_distance

def calc_load_unit_trans_cost():
    print('starting unit transportation cost calculations...')
    product_unit_trans_costs = []
    with engine.connect() as conn:
        dc_store_dists = _calc_dc_store_dists(conn)
        product_df = pd.read_sql(text("select pn, price from product"), conn)
        for _, product_row in product_df.iterrows():
            product_pn = product_row['pn']
            product_price = product_row['price']
            for (store_id, dc_id), dist in dc_store_dists.items():
                unit_trans_cost = _calc_unit_trans_cost(product_price, dist)
                product_unit_trans_costs.append({
                    'product_pn': product_pn,
                    'store_id': store_id,
                    'dc_id': dc_id,
                    'cost': unit_trans_cost
                })
        _write_unit_trans_costs(conn, product_unit_trans_costs)
        conn.commit()

    print('Unit transportation cost calculations completed and saved to database.')

def _write_unit_trans_costs(conn, product_unit_trans_costs: list):
    print(f'Writing {len(product_unit_trans_costs)} unit transportation cost rows to database...')
    conn.execute(text("DELETE FROM product_trans_cost"))
    conn.execute(
        text("""
            INSERT INTO product_trans_cost (product_pn, store_id, dc_id, cost)
            VALUES (:product_pn, :store_id, :dc_id, :cost)
        """),
        product_unit_trans_costs
    )

def _calc_dc_store_dists(conn) -> dict:
    store_query = text("select * from store_location where state in :states").bindparams(
        bindparam('states', expanding=True)
    )
    store_df = pd.read_sql(store_query, conn, params={'states': list(STATE_SUBSET)})

    dc_query = text("select * from dist_center_location where state in :states").bindparams(
                bindparam('states', expanding=True)
            )
    dc_df = pd.read_sql(dc_query, conn, params={'states': list(STATE_SUBSET)})

    print('Computing distances between distribution centers and stores...')
    dc_store_dists = {}
    for _, store_row in store_df.iterrows():
        for _, dc_row in dc_df.iterrows():
            dist = haversine_distance(store_row['lat'], store_row['lon'], dc_row['lat'], dc_row['lon'])
            dc_store_dists[(store_row['store_id'], dc_row['dc_id'])] = dist
    return dc_store_dists

def _calc_unit_trans_cost(sell_price: float, dist: float) -> float:
    return (dist/8000)*sell_price