import pandas as pd
from flask_caching import Cache
from sqlalchemy import create_engine, Connection, text

engine = create_engine('sqlite:///../data/oreilly_network.db', echo=False)

# Shared server-side cache; initialized against the Flask server in app.py via
# cache.init_app(...). Used to hold live pyomo models keyed by aio_id so AIO
# callbacks can retrieve them across separate requests / gunicorn workers.
cache = Cache()

STATE_SUBSET=('FL', 'GA', 'AL', 'TN', 'SC', 'NC', 'VA', 'KY', 'MS', 'WV')

# Shared by every map in the app so the overview and results views frame the
# same region.
MAP_CENTER = (34.0, -84.0)

GRID_D3_CURRENCY_3_DECIMAL = 'd3.format("($.3f")(params.value)'

# Brand tokens mirrored from assets/theme.css so the Plotly figures read as
# part of the same theme as the surrounding chrome. Keep the two in sync.
BRAND_GREEN = '#00713C'
BRAND_RED = '#C8102E'
MAP_STORE_GRAY = '#8A8F8B'

def gen_product_options(conn: Connection):
    options = []
    product_df = pd.read_sql(text("select pn, desc from product"), conn)
    for _, row in product_df.iterrows():
        options.append({'label': row['desc'], 'value': row['pn']})
    return options