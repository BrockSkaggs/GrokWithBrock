import plotly.colors as pc
import plotly.graph_objects as go
import pyomo.environ as pe
from sqlalchemy import text, bindparam
from typing import Tuple

from common import engine, MAP_CENTER, MAP_STORE_GRAY

# Shipped-unit values are continuous; treat anything below this as zero.
_UNITS_EPS = 1e-6

# Mode-select sentinel meaning "every product", shared with the results view.
ALL_PRODUCTS = '__ALL__'

# One color per distribution center. Dark24 holds 24 entries and the model can
# carry a few more DCs than that, so callers index into it modulo its length.
_DC_PALETTE = pc.qualitative.Dark24

def gen_product_dist_center_store_plan(product_pn: str, model: pe.ConcreteModel):
    """Per-distribution-center draw-down plan for a single product.

    Returns a list of dicts (one per DC in the model, including the ones the
    solution never ships from, which come back with units_used 0) ready for the
    detail-card AG Grid. Each dict has:
      - location:   "City, ST" display label
      - units_used: total units shipped out of the DC for this product
      - pct_change: final % change of the DC's inventory (negative drawdown)
      - original:   original DC inventory for this product (used by the caller
                    to total the overall drawdown; ignored by the grid)
    """
    plan = []
    for d in model.dist_centers:
        units_used = sum(pe.value(model.x[d, s, product_pn]) for s in model.stores)
        if units_used <= _UNITS_EPS:
            units_used = 0.0
        original = model.dist_center_inv[d, product_pn]
        # Guard units_used too, so an idle DC reads as 0.0% instead of -0.0%.
        pct_change = -(units_used / original) * 100 if units_used and original else 0
        plan.append({
            'dc_id': d,
            'units_used': units_used,
            'pct_change': pct_change,
            'original': original,
        })

    if not plan:
        return plan

    dc_ids = [row['dc_id'] for row in plan]
    location_query = text(
        "select dc_id, city, state from dist_center_location where dc_id in :dc_ids"
    ).bindparams(bindparam('dc_ids', expanding=True))
    with engine.connect() as conn:
        result = conn.execute(location_query, {'dc_ids': dc_ids})
        locations = {row.dc_id: f"{row.city}, {row.state}" for row in result}

    for row in plan:
        row['location'] = locations.get(row.pop('dc_id'), '')

    # Idle DCs all tie at zero, so fall back to the label to keep their order
    # stable rather than however the model's set happened to iterate.
    plan.sort(key=lambda row: (-row['units_used'], row['location']))
    return plan

def gen_product_store_plan(product_pn: str, model: pe.ConcreteModel):
    """Store-level delivery plan for a single product.

    Returns a list of dicts (one per DC -> store lane that actually ships units)
    ready for the detail-card AG Grid. Each dict has:
      - dc_location:    "City, ST" display label of the shipping DC
      - store_location: "<store_id> - City, ST" display label of the store
      - units:          units to deliver over that lane
    """
    plan = []
    for d in model.dist_centers:
        for s in model.stores:
            units = pe.value(model.x[d, s, product_pn])
            if units <= _UNITS_EPS:
                continue
            plan.append({
                'dc_id': d,
                'store_id': s,
                'units': units,
            })

    if not plan:
        return plan

    dc_ids = sorted({row['dc_id'] for row in plan})
    store_ids = sorted({row['store_id'] for row in plan})

    dc_query = text(
        "select dc_id, city, state from dist_center_location where dc_id in :dc_ids"
    ).bindparams(bindparam('dc_ids', expanding=True))
    store_query = text(
        "select store_id, city, state from store_location where store_id in :store_ids"
    ).bindparams(bindparam('store_ids', expanding=True))
    with engine.connect() as conn:
        dc_locations = {
            row.dc_id: f"{row.city}, {row.state}"
            for row in conn.execute(dc_query, {'dc_ids': dc_ids})
        }
        store_locations = {
            row.store_id: f"{row.store_id} - {row.city}, {row.state}"
            for row in conn.execute(store_query, {'store_ids': store_ids})
        }

    for row in plan:
        row['dc_location'] = dc_locations.get(row.pop('dc_id'), '')
        row['store_location'] = store_locations.get(row.pop('store_id'), '')

    plan.sort(key=lambda row: (row['dc_location'], row['store_location']))
    return plan

def _gen_route_map_layout() -> dict:
    """Layout shared by the populated and empty route maps.

    Mirrors the overview map in app.py so both views frame the same region and
    carry the same legend placement.
    """
    return {
        'map': {
            'center': {'lat': MAP_CENTER[0], 'lon': MAP_CENTER[1]},
            'style': 'carto-positron',
            'zoom': 4.8
        },
        'margin': {'t': 0, 'b': 0, 'l': 0, 'r': 0},
        # One legend entry per DC adds up, so shrink the type and let the legend
        # wrap along the bottom of the map.
        'legend': {
            'orientation': 'h',
            'yanchor': 'top',
            'xanchor': 'right',
            'y': 0,
            'x': 1,
            'font': {'size': 10}
        }
    }

def gen_shipped_lanes(product_pn: str, model: pe.ConcreteModel) -> Tuple[dict, float] :
    """Units shipped over each distribution center -> store lane.

    Returns {(dc_id, store_id): units}, aggregated across every product when
    product_pn is ALL_PRODUCTS, restricted to that product otherwise. Lanes that
    ship nothing are left out.
    """
    products = list(model.products) if product_pn == ALL_PRODUCTS else [product_pn]
    # A product the model never saw has no lanes; drop it rather than letting the
    # var lookup below raise.
    products = [p for p in products if p in model.products]

    lanes = {}
    trans_cost = 0
    for d in model.dist_centers:
        for s in model.stores:
            units = sum(pe.value(model.x[d, s, p]) for p in products)
            if units <= _UNITS_EPS:
                continue
            lanes[(d, s)] = units
            if product_pn != ALL_PRODUCTS:
                trans_cost += model.trans_cost[d,s,product_pn]*units
    return lanes, trans_cost

def gen_route_map(product_pn: str, model: pe.ConcreteModel) -> go.Figure:
    """Map of the shipping lanes the solution calls for.

    Draws a line from a distribution center to a store wherever the solution
    ships units between them, with every lane out of a DC sharing that DC's
    color. product_pn may be ALL_PRODUCTS to aggregate across all products.
    """
    lanes, _ = gen_shipped_lanes(product_pn, model)
    if not lanes:
        return go.Figure(layout=_gen_route_map_layout())

    dc_ids = sorted({d for d, _ in lanes})
    store_ids = sorted({s for _, s in lanes})

    dc_query = text(
        "select dc_id, city, state, lat, lon from dist_center_location where dc_id in :dc_ids"
    ).bindparams(bindparam('dc_ids', expanding=True))
    store_query = text(
        "select store_id, city, state, lat, lon from store_location where store_id in :store_ids"
    ).bindparams(bindparam('store_ids', expanding=True))
    with engine.connect() as conn:
        dcs = {
            row.dc_id: {'label': f"{row.city}, {row.state}", 'lat': row.lat, 'lon': row.lon}
            for row in conn.execute(dc_query, {'dc_ids': dc_ids})
        }
        stores = {
            row.store_id: {'label': f"{row.store_id} - {row.city}, {row.state}",
                           'lat': row.lat, 'lon': row.lon}
            for row in conn.execute(store_query, {'store_ids': store_ids})
        }

    # Color off the model's full DC roster rather than the DCs in this view, so
    # a DC keeps its color as the user switches products.
    dc_colors = {
        d: _DC_PALETTE[i % len(_DC_PALETTE)]
        for i, d in enumerate(sorted(model.dist_centers))
    }

    line_traces = []
    dc_shipped = {}
    store_received = {}
    for d in dc_ids:
        dc = dcs[d]
        lats, lons, hover = [], [], []
        for (lane_dc, lane_store), units in lanes.items():
            if lane_dc != d:
                continue
            store = stores[lane_store]
            dc_shipped[d] = dc_shipped.get(d, 0) + units
            store_received[lane_store] = store_received.get(lane_store, 0) + units
            # None breaks the polyline so every lane draws as its own segment,
            # keeping one trace (and one legend entry) per DC.
            lats.extend([dc['lat'], store['lat'], None])
            lons.extend([dc['lon'], store['lon'], None])
            lane_text = f"{dc['label']} → {store['label']}<br>Units: {units:,.0f}"
            hover.extend([lane_text, lane_text, None])

        line_traces.append(go.Scattermap(
            lat=lats,
            lon=lons,
            mode='lines',
            text=hover,
            hoverinfo='text',
            opacity=0.6,
            line=go.scattermap.Line(width=1.5, color=dc_colors[d]),
            name=dc['label'],
            legendgroup=str(d)
        ))

    dc_marker_trace = go.Scattermap(
        lat=[dcs[d]['lat'] for d in dc_ids],
        lon=[dcs[d]['lon'] for d in dc_ids],
        mode='markers',
        text=[f"{d} - {dcs[d]['label']}<br>Units shipped: {dc_shipped[d]:,.0f}" for d in dc_ids],
        hoverinfo='text',
        marker=go.scattermap.Marker(
            size=12,
            color=[dc_colors[d] for d in dc_ids]
        ),
        showlegend=False,
        name='Dist. Centers'
    )

    store_marker_trace = go.Scattermap(
        lat=[stores[s]['lat'] for s in store_ids],
        lon=[stores[s]['lon'] for s in store_ids],
        mode='markers',
        text=[f"{stores[s]['label']}<br>Units received: {store_received[s]:,.0f}" for s in store_ids],
        hoverinfo='text',
        marker=go.scattermap.Marker(
            size=6,
            color=MAP_STORE_GRAY,
            opacity=0.6
        ),
        showlegend=False,
        name='Stores'
    )

    # Markers last so they sit on top of the lanes.
    return go.Figure(
        data=line_traces + [dc_marker_trace, store_marker_trace],
        layout=_gen_route_map_layout()
    )
