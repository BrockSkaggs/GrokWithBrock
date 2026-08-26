import pyomo.environ as pe
import pandas as pd
from sqlalchemy import create_engine, text, bindparam

engine = create_engine("sqlite:///oreilly_network.db")
STATE_SUBSET=('FL', 'GA', 'AL', 'TN', 'SC', 'NC', 'VA', 'KY', 'MS', 'WV')

def query_dist_center_supply(conn):
    DC_SUPPLY_MAP = """select dcps.*
							from dist_center_product_supply dcps
							join (select dc_id from dist_center_location where state in :states) a on dcps.dc_id = a.dc_id;"""

    dc_supply_df = pd.read_sql(text(DC_SUPPLY_MAP).bindparams(
                                    bindparam('states', expanding=True)
                                ), conn, params={'states': list(STATE_SUBSET)})

    dc_supply_df['amount'] = dc_supply_df['amount'] +500 #Artifical increase in supply to avoid infeasibility in the model
    return dc_supply_df

def gen_dist_center_supply_map(conn):
    dc_supply_df = query_dist_center_supply(conn)
    dc_ids = dc_supply_df['dc_id'].unique().tolist()
    product_pns = dc_supply_df['product_pn'].unique().tolist()
    return dc_supply_df.set_index(['dc_id', 'product_pn'])['amount'].to_dict(), dc_ids, product_pns

def query_store_product_demand(conn):
    STORE_DEMAND_SQL = """select spd.*
								from store_product_demand spd
								join snowfall s on spd.store_id = s.store_id;"""

    return pd.read_sql(text(STORE_DEMAND_SQL), conn)

def gen_store_product_demand_map(conn):
    store_demand_df = query_store_product_demand(conn)
    store_ids = store_demand_df['store_id'].unique().tolist()
    return store_demand_df.set_index(['store_id', 'product_pn'])['amount'].to_dict(), store_ids

def gen_trans_cost_map(conn):
    TRANS_COST_SQL = """select ptc.* 
							from product_trans_cost ptc 
							join snowfall s on ptc.store_id = s.store_id;"""

    trans_cost_df = pd.read_sql(text(TRANS_COST_SQL), conn)
    return trans_cost_df.set_index(['dc_id', 'store_id', 'product_pn'])['cost'].to_dict()

def get_products(conn):
    df = pd.read_sql(text("select pn, desc from product;"), conn)
    return df

def gen_model(enforce_single_delivery: bool = False, M = 10000):
    """
        If M is an integer, then set it globally.
        If M is a dictionary, then make assume it is for each combination of dist center and store..
    """

    with engine.connect() as conn:
        dc_product_supply_map, dc_ids, product_pns = gen_dist_center_supply_map(conn)
        store_product_demand_map, store_ids = gen_store_product_demand_map(conn)
        trans_cost_map = gen_trans_cost_map(conn)

    model = pe.ConcreteModel(name='oreilly_network')
    
    #Sets
    model.dist_centers = pe.Set(initialize=dc_ids)
    model.stores = pe.Set(initialize=store_ids)
    model.products = pe.Set(initialize=product_pns)
    
    #Params
    model.dist_center_inv = pe.Param(model.dist_centers, model.products, initialize=dc_product_supply_map)
    model.store_demands = pe.Param(model.stores, model.products, initialize=store_product_demand_map)
    model.trans_cost = pe.Param(model.dist_centers, model.stores, model.products, initialize=trans_cost_map)
    
    #Variables
    model.x = pe.Var(model.dist_centers, model.stores, model.products, domain=pe.NonNegativeReals)
    model.dc_store_flag = pe.Var(model.dist_centers, model.stores, domain=pe.Binary)
    
    #Objective
    total_trans_cost = sum(model.x[d,s,p]*model.trans_cost[d,s,p] for d in model.dist_centers for s in model.stores for p in model.products)
    model.obj = pe.Objective(expr=total_trans_cost, sense = pe.minimize)
    
    #Constraints
    model.store_reqs = pe.ConstraintList()
    for s in model.stores:
        for p in model.products:
            lhs = sum(model.x[d,s,p] for d in model.dist_centers)
            rhs = model.store_demands[s,p]
            model.store_reqs.add(lhs == rhs)
    
    model.dist_center_supplies = pe.ConstraintList()
    for d in model.dist_centers:
        for p in model.products:
            lhs = sum(model.x[d,s,p] for s in model.stores)
            rhs = model.dist_center_inv[d,p]
            model.dist_center_supplies.add(lhs <= rhs)
    
    if enforce_single_delivery:
        model.dist_center_store_limits = pe.ConstraintList()
        for s in model.stores:
            lhs = sum(model.dc_store_flag[d,s] for d in model.dist_centers)
            model.dist_center_store_limits.add(lhs <= 1)
        
        M_is_dict = isinstance(M, dict)
        model.big_m_1 = pe.ConstraintList()
        for d in model.dist_centers:
            for s in model.stores:
                lhs = sum(model.x[d,s,p] for p in model.products)
                big_M = M if not M_is_dict else M[s]
                rhs = big_M*model.dc_store_flag[d,s]
                model.big_m_1.add(lhs <= rhs)
        
        model.big_m_2 = pe.ConstraintList()
        for d in model.dist_centers:
            for s in model.stores:
                lhs = sum(model.x[d,s,p] for p in model.products)
                rhs = 0.001*model.dc_store_flag[d,s]
                model.big_m_2.add(lhs >= rhs)
    return model

def _gen_raw_model_plan_df(model: pe.ConcreteModel) -> pd.DataFrame:
    plan_dets = []
    for p in model.products:
        for d in model.dist_centers:
            for s in model.stores:
                if pe.value(model.x[d,s,p]) > 0.1:
                    plan_dets.append({
                        'product': p,
                        'dist_center': d,
                        'store': s,
                        'qty': pe.value(model.x[d,s,p])
                    })
    return pd.DataFrame(plan_dets)

def annotate_model_plan(model: pe.ConcreteModel) -> pd.DataFrame:
    plan_df = _gen_raw_model_plan_df(model)
    
    with engine.connect() as conn:
        product_df = get_products(conn)
        product_desc_map = product_df.set_index('pn')['desc'].to_dict()
        dist_center_city_df = pd.read_sql(text("select dc_id, city || ', ' || state as location from dist_center_location;"), conn)
        dist_center_loc_map = dist_center_city_df.set_index('dc_id')['location'].to_dict()
        store_city_df = pd.read_sql(text("select store_id, city || ', ' || state as location from store_location;"), conn)
        store_city_loc_map = store_city_df.set_index('store_id')['location'].to_dict()

    plan_df['product_desc'] = plan_df['product'].map(product_desc_map)
    plan_df['dist_center_loc'] = plan_df['dist_center'].map(dist_center_loc_map)
    plan_df['store_city_loc'] = plan_df['store'].map(store_city_loc_map)
    ordered_cols = ['product', 'product_desc', 'dist_center', 'dist_center_loc', 'store', 'store_city_loc', 'qty']
    plan_df = plan_df[ordered_cols]
    return plan_df
