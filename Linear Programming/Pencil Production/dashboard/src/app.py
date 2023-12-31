import json
from typing import Dict, Tuple
import math

from dash import Dash, html, dcc, clientside_callback, Input, Output, State, callback
import dash_ag_grid as dag
import dash_daq as daq
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from lp_model import solve_lp_model

def read_data_file() -> dict:
    f =open('data.json')
    data = json.load(f)
    f.close()
    return data

data = read_data_file()

app = Dash(__name__)
server = app.server #Exposing Flask server for gunicorn

app.layout = html.Div([
    html.Div([
        html.Div([
            dbc.Card(dbc.CardBody([
                html.H1('Pencil Production')
            ]))
        ], className='col-12')
    ], className='row'),
    html.Div([
        html.Div([
            dbc.Card(
                dbc.CardBody([
                    dbc.Tabs([
                        dbc.Tab([
                            html.Div([
                                html.Div([
                                    html.Div([
                                        dbc.Card(
                                            dbc.CardBody([
                                                html.Div([
                                                    daq.Knob(
                                                        id='economy_units_knob',
                                                        max=10000,
                                                        value=1000,
                                                        className='text-center',
                                                        color='#007bff'
                                                    ),
                                                    html.Div([], id='economy_knob_label', className='text-center'),
                                                ], className='d-inline-block', style={'width': '33%'}),
                                                html.Div([
                                                    daq.Knob(
                                                        id='deluxe_units_knob',
                                                        max=10000,
                                                        value=1000,
                                                        className='text-center',
                                                        color='#007bff'
                                                    ),
                                                    html.Div([], id='deluxe_knob_label', className='text-center'),
                                                ], className='d-inline-block', style={'width': '33%'}),
                                                html.Div([
                                                    html.Div([
                                                        html.P(['Run Model'], style={'fontSize':'larger'}) 
                                                    ], className='d-inline-block run-model-btn', id='run_model_btn'), 
                                                ], style={'width': '33%', 'justifyContent': 'center', 'alignItems': 'center'}, className='text-center d-flex')
                                            ], className='d-flex')
                                        , className='w-100')
                                    ], className='col-lg-6 d-flex'),
                                    html.Div([
                                        dbc.Card(
                                            dbc.CardBody([], id='results_card_body'), style={'height':'100%'}
                                        )
                                    ], className='col-lg-6')
                                ], className='row'),
                                html.Div([
                                    html.Div([
                                        dbc.Card(
                                            dbc.CardBody([
                                                dcc.Graph(id='dept_load_chart')
                                            ])
                                        )
                                    ], className='col-lg-6'),
                                    html.Div([
                                        dbc.Card(
                                            dbc.CardBody([
                                                dcc.Graph(id='inv_load_chart')
                                            ])
                                        )
                                    ], className='col-lg-6')
                                ], className='row mt-1'),
                                html.Div([
                                    html.Div([
                                        html.P('Model uses continuous real decision variables to represent the quantity of each product to produce.  Optimal values are rounded down to the nearest integer.', className='font-italic')
                                    ], className='col-12')
                                ], className='row mt-1')
                            ], className='container-fluid mt-2')
                        ], label='Analysis'),
                        dbc.Tab([
                            html.Div([
                                html.Div([
                                    html.Div([
                                        dbc.Card(
                                            dbc.CardBody([
                                                html.H3('Parts'),
                                                dag.AgGrid(
                                                    id='parts_grid',
                                                    defaultColDef={'editable':True},
                                                    columnSize='responsiveSizeToFit',
                                                    columnDefs=[
                                                        {'field': 'part', 'headerName': 'Part'},
                                                        {'field': 'cost', 'headerName': 'Cost', 'valueFormatter': {"function": "'$' + (params.value)"}},
                                                        {'field': 'inv', 'headerName': 'Inventory', 'valueFormatter': {"function": "d3.format(',')(params.value)"}},
                                                        {'field': 'uom', 'headerName': 'UOM'},
                                                    ],
                                                    rowData=data['parts']
                                                )
                                            ])
                                        )
                                    ], className='col-lg-6'),
                                    html.Div([
                                        dbc.Card(
                                            dbc.CardBody([
                                                html.H3('BOM'),
                                                dag.AgGrid(
                                                    id='bom_grid',
                                                    defaultColDef={'editable':True},
                                                    columnSize='responsiveSizeToFit',
                                                    columnDefs=[
                                                        {'field': 'part', 'headerName': 'Part'},
                                                        {'field': 'economy', 'headerName': 'Economy'},
                                                        {'field': 'deluxe', 'headerName': 'Deluxe'},
                                                        {'field': 'uom', 'headerName': 'UOM'},
                                                    ],
                                                    rowData=data['bom']
                                                )
                                            ])
                                        )
                                    ], className='col-lg-6'),
                                ], className='row mt-2'),
                                html.Div([
                                    html.Div([
                                        dbc.Card(
                                            dbc.CardBody([
                                                html.H3('Departments'),
                                                dag.AgGrid(
                                                    id='dept_grid',
                                                    defaultColDef={'editable':True},
                                                    columnSize='responsiveSizeToFit',
                                                    columnDefs=[
                                                        {'field': 'dept', 'headerName': 'Department'},
                                                        {'field': 'economy', 'headerName': 'Economy (Seconds)'},
                                                        {'field': 'deluxe', 'headerName': 'Deluxe (Seconds)'},
                                                        {'field': 'capacity', 'headerName': 'Capacity (Hours)'},
                                                    ],
                                                    rowData=data['dept']
                                                )
                                            ])
                                        )
                                    ], className='col-lg-6'),
                                    html.Div([
                                        dbc.Card(
                                            dbc.CardBody([
                                                html.Div([
                                                    html.Div([
                                                        html.Div([
                                                            html.H3('Finance')
                                                        ], className='col-12')
                                                    ], className='row'),
                                                    html.Div([
                                                        html.Div([
                                                            html.Span("Economy Price ($)")
                                                        ], className='col-3'),
                                                        html.Div([
                                                            dcc.Input(
                                                                id='economy_price_input',
                                                                value=data['economy_price'],
                                                                type='number',
                                                                min=0.01,
                                                                max=10.00,
                                                                step=0.01
                                                            )   
                                                        ], className='col-3'),
                                                        html.Div([
                                                            html.Span('Shop Labor ($/minute)')
                                                        ], className='col-3'),
                                                        html.Div([
                                                            dcc.Input(
                                                                id='shop_rate_input',
                                                                value=data['shop_labor_rate'],
                                                                type='number',
                                                                min=0.01,
                                                                max=10.00,
                                                                step=0.01
                                                            )
                                                        ], className='col-3')                    
                                                    ], className='row'),
                                                    html.Div([
                                                        html.Div([
                                                            html.Span("Deluxe Price ($)")
                                                        ], className='col-3'),
                                                        html.Div([
                                                            dcc.Input(
                                                                id='deluxe_price_input',
                                                                value=data['deluxe_price'],
                                                                type='number',
                                                                min=0.01,
                                                                max=10.00,
                                                                step=0.01
                                                            )   
                                                        ], className='col-3')
                                                    ], className='row mt-2')
                                                ], className='container-fluid')
                                            ]), style={'height':'100%'}
                                        )
                                    ], className='col-lg-6')
                                ], className='row mt-2')
                            ], className='container-fluid')
                        ], label='Data Maint.')
                    ])
                ])
            )
        ], className='col-12')
    ], className='row mt-2')
], className='container-fluid mt-1')


clientside_callback(
    """
    function(knob_value){
        return "Economy Units: " + knob_value.toLocaleString(undefined, {maximumFractionDigits:1})
    }
    """,
    Output('economy_knob_label', 'children'),
    Input('economy_units_knob', 'value')
)

clientside_callback(
    """
    function(knob_value){
        return "Deluxe Units: " + knob_value.toLocaleString(undefined, {maximumFractionDigits:1})
    }
    """,
    Output('deluxe_knob_label', 'children'),
    Input('deluxe_units_knob', 'value')
)


def calc_bar_color(load_frac: float) -> str:
    return 'crimson' if load_frac > 1 else 'lightslategray'

def gen_dept_load_figure(econ_units, deluxe_units, ui_data) -> Dict[go.Figure, pd.DataFrame]:
    dept_loads = []
    bar_colors = []
    bar_txts = []
    for item in ui_data['dept']:
        load = econ_units*item['economy']/3600 + deluxe_units*item['deluxe']/3600
        load_frac = load/item['capacity']
        bar_colors.append(calc_bar_color(load_frac))
        dept_loads.append({
            'dept': item['dept'],
            'load': load,
            'load_frac': load_frac,
            'capacity': item['capacity']
        })
        bar_txts.append(f"{load_frac*100:.1f}%")
    dept_load_df = pd.DataFrame(dept_loads)
    
    traces = [
        go.Bar(name='Capacity', 
            x=dept_load_df['dept'], 
            y=dept_load_df['load_frac'], 
            marker_color=bar_colors,
            text=bar_txts,
            textposition='auto'
            )
    ]

    layout = {
        'title': {'text':'Department Loads', 'font': {'size': 25}}
    }

    fig =go.Figure(data=traces, layout=layout)
    return fig, dept_load_df

def gen_inv_load_figure(econ_units, deluxe_units, ui_data) -> Dict[go.Figure, pd.DataFrame]:
    part_loads = []
    bar_colors = []
    bar_txts = []
    for bom_item in ui_data['bom']:
        inv_det = next((p for p in ui_data['parts'] if p['part'] == bom_item['part']), None)
        econ_unit_burden = bom_item['economy'] if bom_item['uom'] != 'OZ' else bom_item['economy']/16
        deluxe_unit_burden = bom_item['deluxe'] if bom_item['uom'] != 'OZ' else bom_item['deluxe']/16

        total_burden = econ_units*econ_unit_burden +  deluxe_units*deluxe_unit_burden
        capacity = inv_det['inv']
        load_frac = total_burden/capacity
        bar_colors.append(calc_bar_color(load_frac))
        bar_txts.append(f"{load_frac*100:.1f}%")
        part_loads.append({
            'part': bom_item['part'],
            'load': total_burden,
            'load_frac': load_frac,
            'capacity': capacity
        })
    
    part_loads_df = pd.DataFrame(part_loads)

    traces = [
        go.Bar(name='Inventory',
            x=part_loads_df['part'],
            y=part_loads_df['load_frac'],
            marker_color=bar_colors,
            text=bar_txts,
            textposition='auto'
        )
    ]

    layout = {
        'title': {'text':'Inventory Loads', 'font': {'size': 25}}
    }

    return go.Figure(data=traces, layout=layout), part_loads_df

def gen_results_card(econ_units, deluxe_units, dept_df: pd.DataFrame, inv_df: pd.DataFrame) -> Tuple[list, str]:
    is_feasible = True
    if dept_df[dept_df['load_frac'] > 1].shape[0] > 0 or inv_df[inv_df['load_frac'] > 1].shape[0]:
        is_feasible = False

    soln_status = 'Feasible'
    className= 'center' 
    if not is_feasible:
        className += ' infeasible'
        soln_status = 'InFeasible'
    else:
        className += ' feasible'

    inner_div = html.Div([
        html.H3(f'Solution Status: {soln_status}', className='text-center')
    ])
    if is_feasible:
        inner_div.children.append(html.H3(f"Profit Contribution: ${calc_profit(econ_units, deluxe_units):,.2f}", className='text-center'))
    body_items = [inner_div]
    return body_items, className

def calc_profit(econ_units, deluxe_units) -> float:
    gross_rev = econ_units*data['economy_price'] + deluxe_units*data['deluxe_price']
    labor_costs = 0
    for dept in data['dept']:
        labor_costs += (econ_units*dept['economy']/3600 + deluxe_units*dept['deluxe']/3600)*data['shop_labor_rate']*60

    matl_costs = 0
    for part_det in data['parts']:
        unit_cost = float(part_det['cost'])
        part_bom = next((b for b in data['bom'] if b['part'] == part_det['part']), None)
        econ_part_unit_used = part_bom['economy']
        deluxe_part_unit_used = part_bom['deluxe']
        if part_bom['uom'] == 'OZ':
            econ_part_unit_used = econ_part_unit_used/16
            deluxe_part_unit_used = deluxe_part_unit_used/16
        matl_costs += (econ_units*econ_part_unit_used + deluxe_units*deluxe_part_unit_used)*unit_cost
    return gross_rev - labor_costs - matl_costs

def cond_ui_data(econ_price, deluxe_price, shop_rate, dept_rows, bom_rows, part_rows) -> dict:    
    for dept in dept_rows:
        dept['economy'] = float(dept['economy'])
        dept['deluxe'] = float(dept['deluxe'])
        dept['capacity'] = float(dept['capacity'])

    for part in part_rows:
        part['cost'] = float(part['cost'])
        part['inv'] = float(part['inv'])

    for part in bom_rows:
        part['economy'] = float(part['economy'])
        part['deluxe'] = float(part['deluxe'])

    return {
        'economy_price': econ_price,
        'deluxe_price': deluxe_price,
        'shop_labor_rate': shop_rate,
        'parts': part_rows,
        'bom': bom_rows,
        'dept': dept_rows
    }

@callback(
    Output('economy_units_knob', 'value'),
    Output('deluxe_units_knob', 'value'),
    Input('run_model_btn', 'n_clicks'),
    State("economy_price_input", "value"),
    State('deluxe_price_input', 'value'),
    State('shop_rate_input', 'value'),
    State('dept_grid', 'rowData'),
    State('bom_grid', 'rowData'),
    State('parts_grid', 'rowData'),
    prevent_initial_call=True
)
def run_lp_model(_, econ_price, deluxe_price, shop_rate, dept_rows, bom_rows, part_rows):
    ui_data = cond_ui_data(econ_price, deluxe_price, shop_rate, dept_rows, bom_rows, part_rows)
    econ_units, deluxe_units = solve_lp_model(ui_data)
    cond_econ_units, cond_deluxe_units = math.floor(econ_units), math.floor(deluxe_units)
    return cond_econ_units, cond_deluxe_units

@callback(
    Output('dept_load_chart', 'figure'),
    Output('inv_load_chart', 'figure'),
    Output('results_card_body', 'children'),
    Output('results_card_body', 'className'),
    Input('economy_units_knob', 'value'),
    Input('deluxe_units_knob', 'value'),
    State("economy_price_input", "value"),
    State('deluxe_price_input', 'value'),
    State('shop_rate_input', 'value'),
    State('dept_grid', 'rowData'),
    State('bom_grid', 'rowData'),
    State('parts_grid', 'rowData'),
)
def update_post_calc(econ_units, deluxe_units, econ_price, deluxe_price, shop_rate, dept_rows, bom_rows, part_rows):
    ui_data = cond_ui_data(econ_price, deluxe_price, shop_rate, dept_rows, bom_rows, part_rows)
    dept_fig, dept_df = gen_dept_load_figure(econ_units, deluxe_units, ui_data)
    inv_fig, inv_df = gen_inv_load_figure(econ_units, deluxe_units, ui_data)
    results_body, results_class = gen_results_card(econ_units, deluxe_units, dept_df, inv_df)
    return dept_fig, inv_fig, results_body, results_class


if __name__ == '__main__':
    app.run(debug=True)