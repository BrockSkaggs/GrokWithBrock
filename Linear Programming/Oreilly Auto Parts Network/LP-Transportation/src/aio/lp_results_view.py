from dash import html, dcc, callback, Input, Output, State, MATCH
from dash_ag_grid import AgGrid
from dash_bootstrap_components import Card, CardBody
import dash_mantine_components as dmc
import plotly.graph_objects as go
import pyomo.environ as pe
from uuid import uuid4

from common import engine, gen_product_options, cache
import lp_review as lp_rev

class LpResultsView(html.Div):
    
    class ids:
        mode_select = lambda aio_id: {
            'component': 'LpResultsView',
            'subcomponent': 'mode_select',
            'aio_id': aio_id
        }

        results_route_map = lambda aio_id: {
            'component': 'LpResultsView',
            'subcomponent': 'results_route_map',
            'aio_id': aio_id
        }

        summary_div = lambda aio_id: {
            'component': 'LpResultsView',
            'subcomponent': 'summary_div',
            'aio_id': aio_id
        }

        detail_card = lambda aio_id: {
            'component': 'LpResultsView',
            'subcomponent': 'detail_card',
            'aio_id': aio_id
        }

    ids = ids

    def __init__(self, model: pe.ConcreteModel, aio_id = None):
        if aio_id is None:
            aio_id = str(uuid4())
        cache.set(f'lp_model:{aio_id}', model)   # pickled into the shared FileSystemCache
        super().__init__(self._gen_layout(aio_id))


    def _gen_layout(self, aio_id):
        mode_options = [{'label': 'All', 'value':lp_rev.ALL_PRODUCTS}]
        with engine.connect() as conn:
            mode_options.extend(gen_product_options(conn))

        return html.Div([
            html.Div([
                html.Div([
                    Card(
                        CardBody([
                            html.Div([
                                html.Div([
                                    html.Div([
                                        dmc.Select(id=self.ids.mode_select(aio_id), 
                                                   data=mode_options,
                                                   value=lp_rev.ALL_PRODUCTS,
                                                   allowDeselect=False)
                                    ], className='col-lg-3'),
                                    html.Div([], className='col-lg-9', id=self.ids.summary_div(aio_id))
                                ], className='row mb-2'),
                                html.Div([
                                    html.Div([
                                        Card(CardBody([
                                            'Details Here'
                                        ], id=self.ids.detail_card(aio_id),
                                            className='d-flex flex-column'), className='h-100')
                                    ], className='col-lg-3'),
                                    html.Div([
                                        # h-100 + d-flex lets the graph's flex-grow-1 claim
                                        # whatever height the row gives the card.
                                        Card(CardBody(
                                            dcc.Graph(
                                                id=self.ids.results_route_map(aio_id),
                                                className='mt-2 flex-grow-1',
                                                style={'minHeight':'700px'},
                                                responsive=True
                                            ),
                                            className='d-flex flex-column'
                                        ), className='h-100')
                                    ], className='col-lg-9')
                                ], className='row')
                            ], className='container-fluid')
                        ])
                    )
                ], className='col-12')
            ], className='row')
        ], className='container-fluid mt-2')

    @callback(
        Output(ids.summary_div(MATCH), 'children'),
        Input(ids.mode_select(MATCH), 'value'),
        State(ids.summary_div(MATCH), 'id')
    )
    def load_summary_controls(mode: str, comp_id: dict):
        model = cache.get(f"lp_model:{comp_id['aio_id']}")
        if model is None:
            return dmc.Alert('Results expired — please re-run the model.', color='yellow')

        total_cost = pe.value(model.obj)

        if mode == lp_rev.ALL_PRODUCTS:
            return html.Span(f"Total Shipping Cost: ${total_cost:,.2f}",
                             className='summary-metric')

        _, part_trans_cost = lp_rev.gen_shipped_lanes(mode, model)
        return html.Span(
            f"Part Shipping Cost: ${part_trans_cost:,.2f} "
            f"({(part_trans_cost/total_cost)*100:.1f}% of Total)",
            className='summary-metric')

    @callback(
        Output(ids.detail_card(MATCH), 'children'),
        Input(ids.mode_select(MATCH), 'value'),
        State(ids.detail_card(MATCH), 'id')
    )
    def load_product_detail_card(mode: str, comp_id: dict):
        model = cache.get(f"lp_model:{comp_id['aio_id']}")
        if model is None:
            return 'Results expired — please re-run the model.'

        dist_center_usage_header = html.H5('Distribution Center Usage', className='mb-2')
        dist_plan_header = html.H5('Distribution Plan', className='mt-2 mb-2')

        if mode == lp_rev.ALL_PRODUCTS:
            return [
                dist_center_usage_header,
                html.Span('Select a part to view distribution center usage.', className='fst-italic text-muted'),
                dist_plan_header,
                html.Span('Select a part to view distribution plan.', className='fst-italic text-muted')
            ]

        rows = lp_rev.gen_product_dist_center_store_plan(mode, model)

        total_used = sum(row['units_used'] for row in rows)
        total_inv = sum(row['original'] for row in rows)
        overall_pct = -(total_used / total_inv) * 100 if total_inv else 0
        totals_row = {'location': 'Total', 'units_used': total_used, 'pct_change': overall_pct}

        column_defs = [
            {'headerName': 'Distribution Center', 'field': 'location', 'maxWidth': 150},
            {'headerName': 'Units Used', 'field': 'units_used', 'flex': 1, 'type': 'rightAligned',
                'valueFormatter': {'function': "d3.format(',')(params.value)"}},
            {'headerName': 'Inventory Change', 'field': 'pct_change', 'flex': 1, 'type': 'rightAligned',
                'valueFormatter': {'function': "d3.format('.1f')(params.value) + '%'"}},
        ]

        store_rows = lp_rev.gen_product_store_plan(mode, model)
        store_totals_row = {
            'dc_location': 'Total',
            'store_location': '',
            'units': sum(row['units'] for row in store_rows)
        }

        store_column_defs = [
            {'headerName': 'Distribution Center', 'field': 'dc_location', 'flex': 2},
            {'headerName': 'Store', 'field': 'store_location', 'flex': 2},
            {'headerName': 'Quantity', 'field': 'units', 'flex': 1, 'type': 'rightAligned',
                'valueFormatter': {'function': "d3.format(',.0f')(params.value)"}},
        ]

        return [
            dist_center_usage_header,
            AgGrid(
                rowData=rows,
                columnDefs=column_defs,
                defaultColDef={'sortable': True, 'resizable': True},
                dashGridOptions={
                    'domLayout': 'autoHeight',
                    'pinnedTopRowData': [totals_row],
                    'getRowStyle': {'function': "params.node.rowPinned ? {'fontWeight': 'bold'} : {}"},
                    'theme': 'themeBalham'
                },
                style={'width': '100%'},
                className='ag-theme-balham'
            ),
            dist_plan_header,
            html.Div(
                AgGrid(
                    rowData=store_rows,
                    columnDefs=store_column_defs,
                    defaultColDef={'sortable': True, 'resizable': True, 'filter':True},
                    dashGridOptions={
                        'pinnedTopRowData': [store_totals_row],
                        'getRowStyle': {'function': "params.node.rowPinned ? {'fontWeight': 'bold'} : {}"},
                        'theme': 'themeBalham'
                    },
                    style={'width': '100%', 'height': '100%'},
                    className='ag-theme-balham'
                ),
                className='flex-grow-1',
                style={'minHeight': '150px'}
            )
        ]

    @callback(
        Output(ids.results_route_map(MATCH), 'figure'),
        Input(ids.mode_select(MATCH), 'value'),
        State(ids.results_route_map(MATCH), 'id')
    )
    def load_route_map(mode: str, comp_id: dict):
        model = cache.get(f"lp_model:{comp_id['aio_id']}")
        if model is None:
            return go.Figure(layout={
                'annotations': [{
                    'text': 'Results expired — please re-run the model.',
                    'showarrow': False,
                    'xref': 'paper', 'yref': 'paper', 'x': 0.5, 'y': 0.5
                }],
                'xaxis': {'visible': False},
                'yaxis': {'visible': False}
            })

        return lp_rev.gen_route_map(mode, model)
