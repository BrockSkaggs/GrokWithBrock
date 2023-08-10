from typing import Tuple, Dict

import pyomo.opt as po
import pyomo.environ as pe

products = ['economy', 'deluxe']

def seconds_to_hours(sec_val: float)->float:
    return sec_val/3600

def oz_to_lb(oz_val: float) -> float:
    return oz_val/16

def calc_unit_matl_costs(data: dict) -> Dict[str, float]:
    matl_cost = {}
    for prod in products:
        m_cost = 0
        for part_det in data['parts']:
            bom_det = next((b for b in data['bom'] if b['part'] == part_det['part']), None)
            amount_used = bom_det[prod]
            if bom_det['uom'] == 'OZ' and part_det['uom'] == 'LB':
                amount_used = oz_to_lb(amount_used)
            m_cost += amount_used*float(part_det['cost'])
        matl_cost[prod] =m_cost
    return matl_cost

def calc_unit_labor_costs(data: dict) -> Dict[str, float]:
    labor_cost = {}
    for prod in products:
        l_time = 0 
        for dept_det in data['dept']:
            l_time += seconds_to_hours(dept_det[prod])
        labor_cost[prod] = l_time*float(data['shop_labor_rate']*60)
    return labor_cost

def calc_unit_profit(data: dict) -> Dict[str, float]:
    matl_cost = calc_unit_matl_costs(data)
    labor_cost = calc_unit_labor_costs(data)
    unit_rev = {
        'economy': float(data['economy_price']),
        'deluxe': float(data['deluxe_price'])
    }

    unit_profit = {}
    for prod in products:
        unit_profit[prod] = unit_rev[prod] - matl_cost[prod] - labor_cost[prod]
    return unit_profit

def prep_dept_part_loads(data: dict) -> Tuple[dict, dict]:
    loads = {}
    capacities = {}
    for dept_det in data['dept']:
        dept_name = dept_det['dept'].lower() 
        for prod in products:
            loads[(dept_name, prod)] = seconds_to_hours(dept_det[prod])
        capacities[dept_name] = dept_det['capacity']
    return loads, capacities

def prep_inv_part_loads(data: dict) -> Tuple[dict, dict]:
    capacities = {}
    loads = {}
    
    capacities = {part_det['part'].lower(): int(part_det['inv']) for part_det in data['parts']} 
    
    for bom_item in data['bom']:
        for prod in products:
            amount_used = bom_item[prod]
            if bom_item['uom'] == 'OZ':
                amount_used = oz_to_lb(amount_used)
            loads[(bom_item['part'].lower(), prod)] = amount_used
    return loads, capacities

def build_lp_model(data: dict, unit_profits: Dict[str, float]) -> pe.ConcreteModel:
    dept_unit_loads, dept_capacities = prep_dept_part_loads(data)
    inv_unit_loads, inv_capacities = prep_inv_part_loads(data)

    model = pe.ConcreteModel(name='Pencil Production')
    
    model.x_econ = pe.Var(domain = pe.NonNegativeReals)
    model.x_del = pe.Var(domain = pe.NonNegativeReals)

    obj_expr = model.x_econ*unit_profits['economy'] + model.x_del*unit_profits['deluxe']
    model.obj = pe.Objective(sense = pe.maximize, expr=obj_expr)

    model.dept_loads = pe.ConstraintList()
    for dept in dept_capacities.keys():
        lhs = model.x_econ*dept_unit_loads[dept, 'economy'] +  model.x_del*dept_unit_loads[dept, 'deluxe']
        rhs = dept_capacities[dept]
        model.dept_loads.add(lhs <= rhs)
    
    model.inv_loads = pe.ConstraintList()
    for part in inv_capacities.keys():
        lhs = model.x_econ*inv_unit_loads[part, 'economy'] + model.x_del*inv_unit_loads[part, 'deluxe']
        rhs = inv_capacities[part]
        model.inv_loads.add(lhs <= rhs)
    return model

def run_lp_model(data: dict) -> tuple:
    unit_profits = calc_unit_profit(data)
    model = build_lp_model(data, unit_profits)

    # solver = po.SolverFactory('glpk')
    # result = solver.solve(model, tee=True)

    return 1000,1500