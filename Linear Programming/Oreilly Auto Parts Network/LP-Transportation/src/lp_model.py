import pyomo.environ as pe
from typing import List

def solve_model(dc_ids: List[int], store_ids: List[int], product_pns: List[str],
                dc_product_supply_map: dict,
                store_product_demand_map: dict,
                trans_cost_map: dict):

    model = pe.ConcreteModel(name='oreilly_transportation')

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

    #Objective
    total_trans_costs = sum(model.x[d,s,p]*model.trans_cost[d,s,p] for d in model.dist_centers for s in model.stores for p in model.products)    
    model.obj = pe.Objective(expr=total_trans_costs, sense=pe.minimize)

    #Constraint - Satisfy store demands
    model.store_reqs = pe.ConstraintList()
    for p in model.products:
        for s in model.stores:
            lhs = sum(model.x[d,s,p] for d in model.dist_centers)
            rhs = model.store_demands[s,p]
            model.store_reqs.add(lhs == rhs)

    #Constraint - Don't exceed distribution center inventory
    model.dist_center_supplies = pe.ConstraintList()
    for p in model.products:
        for d in model.dist_centers:
            lhs = sum(model.x[d,s,p] for s in model.stores)
            rhs = model.dist_center_inv[d,p]
            model.dist_center_supplies.add(lhs <= rhs)

    solver = pe.SolverFactory('glpk')
    results = solver.solve(model, tee=True)
    return model


MODEL_MARKDOWN = '''
    **Sets**  
    Distribution Centers    
    $D = \{d_1, d_2, d_3, ...\}$   
    Retail Stores  
    $S = \{s_1, s_2, s_3, ...\}$  
    Products  
    $P = \{p_1, p_2, p_3, ...\}$  

    **Parameters**  
    Amount of inventory of product p at distribution center d  
    $a_{d,p} \in \mathbb{Z} \hspace{2mm} \\forall d \in D, \\forall p \in P$  
    Demand of product p at store s    
    $b_{s,p} \in \mathbb{Z} \hspace{2mm} \\forall s \in S, \\forall p \in P$  
    Unit cost of shipping product p from distribution center d to store s  
    $c_{d,s,p} \in \mathbb{R} \hspace{2mm} \\forall d \in D, \\forall s \in S, \\forall p \in P$  

    **Variables**  
    Quantity of product p to ship from distribution center d to store s  
    $x_{d,s,p} \in \mathbb{R} \hspace{2mm} \\forall d \in D, \\forall s \in S, \\forall p \in P$  

    **Model**  

    $$
    \\begin{array}{cccccl} \\text{min} & \sum_{d \in D} \sum_{s \in S} \sum_{p \in P} x_{d,s,p}c_{d,s,p} & & & \\\\
     \\text{s.t.} & & & & \\\\
     & \sum_{d \in D} x_{d,s,p} & = & b_{s,p} & \\forall s \in S, \\forall p \in P & \\text{Satisfy store demand} \\\\
     & \sum_{s \in S} x_{d,s,p} & \le & a_{d,p} & \\forall d \in D, \\forall p \in P & \\text{Inventory limit at distribution center} \\\\
     & x_{d,s,p} & \ge & 0 & \\forall d \in D, \\forall s \in S, \\forall p \in P
    \\end{array}
    $$

    
'''