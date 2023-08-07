import json

from dash import Dash, html, dcc
import dash_ag_grid as dag
import dash_daq as daq
import dash_bootstrap_components as dbc


def read_data_file() -> dict:
    f =open('data.json')
    data = json.load(f)
    f.close()
    return data

data = read_data_file()

app = Dash(__name__)

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
                                                daq.Knob(
                                                    id='economy_units',
                                                    max=10000,
                                                    value=1000
                                                ),

                                                daq.Knob(
                                                    id='deluxe_units',
                                                    max=10000,
                                                    value=1000
                                                ),
                                            ])
                                        )
                                    ], className='col-lg-3')
                                ], className='row')
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


if __name__ == '__main__':
    app.run(debug=True)