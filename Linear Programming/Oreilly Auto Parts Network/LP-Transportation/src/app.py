from dash import Dash, html, dcc, callback, Input, Output
from dash_ag_grid import AgGrid
from dash_bootstrap_components import Card, CardBody, Tabs, Tab
import dash_mantine_components as dmc
import pandas as pd
import plotly.graph_objs as go
from sqlalchemy import text, bindparam

from aio.lp_results_view import LpResultsView
from common import (engine, MAP_CENTER, STATE_SUBSET, GRID_D3_CURRENCY_3_DECIMAL,
	gen_product_options, cache, BRAND_RED, MAP_STORE_GRAY)
from lp_model import solve_model, MODEL_MARKDOWN

SNOW_MAX_MARKER_PX = 22

app = Dash(__name__)
server = app.server

cache.init_app(server, config={
	'CACHE_TYPE': 'FileSystemCache',
	'CACHE_DIR': '/code/data/cache',   # absolute -> same dir for every gunicorn worker
	'CACHE_DEFAULT_TIMEOUT': 0,        # models don't auto-expire; eviction handled by threshold
	'CACHE_THRESHOLD': 200,            # bound disk usage; oldest entries pruned past this
})

# Mantine needs exactly ten shades and uses index 6 as the filled fill (7-8 for
# hover), so the brand green sits at position 6. Without this the Mantine
# controls render their stock blue against the green Bootstrap chrome.
MANTINE_THEME = {
	'primaryColor': 'oreillyGreen',
	'colors': {
		'oreillyGreen': ['#E8F4EC', '#D2E8DA', '#A9D2B9', '#7CBB96', '#57A77A',
			'#3F9A68', '#00713C', '#006034', '#00512C', '#003F22'],
	},
}

app.layout = dmc.MantineProvider(
	html.Div([
		html.Div([
			html.Div([
				html.H1("O'Reilly Auto Parts - Transportation Problem", id='title')
			], className='col-12')
		], className='row mb-2'),
		html.Div([
			html.Div([
				Tabs([
					Tab(html.Div([
						html.Div([
							html.Div([
								Card(CardBody([
									html.Div([
										html.Div([
											html.Div([
												dmc.Select(id='map_view_select', allowDeselect=False)
											], className='col-lg-3'),
											html.Div([
												html.Span(id='map_view_note', className='fst-italic text-muted', style={'position': 'relative', 'top': '7px'}),
												dmc.Button('Run Model', id='run_model_btn', variant='filled', style={'float': 'right'}),
												dmc.Button('View Model', id='view_model_btn', variant='filled', style={'float': 'right', 'marginRight': '10px'})
											], className='col-lg-9')
										], className='row mb-2'),
										html.Div([
											html.Div([
												Card(CardBody([
													html.H5('Distribution Center Supply', className='mb-2'),
													html.Div(id='supply_sidebar'),
													html.H5('Unit Shipping Costs', className='mt-3 mb-2'),
													html.Div(id='trans_cost_sidebar')
												]), className='h-100')
											], className='col-lg-3'),
											html.Div([
												Card(CardBody(
													dcc.Graph(
														id='location_map',
														className='mt-2 flex-grow-1',
														style={'minHeight': '700px'},
														responsive=True
													),
													className='d-flex flex-column'
												), className='h-100')
											], className='col-lg-9'),
										], className='row')
									], className='container-fluid'),
								]))
							], className='col-12')
						], className='row')
					], className='container-fluid mt-2'), label='Problem Overview', id='problem_tab', tab_id='problem_tab'),
					Tab(['Run model to build tab content.'], label='Solution', id='solution_tab', tab_id='solution_tab')
				], active_tab='problem_tab', id='nav_tabs')
			], className='col-12')
		], className='row'),
		dmc.Modal(id='view_model_modal', size='55%', title=html.H5('Linear Programming Model'))
	], className='container-fluid'),
	theme=MANTINE_THEME
)

def _gen_dist_center_trace(conn) -> go.Scattermap:
	dc_query = text("select * from dist_center_location where state in :states").bindparams(
			bindparam('states', expanding=True)
		)
	dc_df = pd.read_sql(dc_query, conn, params={'states': list(STATE_SUBSET)})
	dc_df['text'] = dc_df['dc_id'].astype(str) + ' - ' + dc_df['street'] + ' - ' + dc_df['city'] + ', ' + dc_df['state']
	return go.Scattermap(
		lat=dc_df['lat'],
		lon=dc_df['lon'],
		mode='markers',
		text=dc_df['text'],
		marker=go.scattermap.Marker(
			size=12,
			color=BRAND_RED
		),
		name='Dist. Centers'
	)

def _gen_snow_affected_sql(metric: str) -> str:
	if metric == 'snowfall':
		return "select store_id, depth_in from snowfall where depth_in > 0;"
	return f"select store_id, amount from store_product_demand where product_pn = :product_pn and amount > 0;"

@callback(
	Output('map_view_select', 'data'),
	Output('map_view_select', 'value'),
	Input('title', 'className')	
)
def load_map_view_options(_):
	options = [{'label': 'Snowfall', 'value': 'snowfall'}]
	with engine.connect() as conn:
		options.extend(gen_product_options(conn))
	return options, 'snowfall'

@callback(
	Output('location_map', 'figure'),
	Output('map_view_note', 'children'),
	Input('map_view_select', 'value')
)
def update_map(map_view: str):
	store_df = pd.DataFrame()
	traces = []
	
	with engine.connect() as conn:
		store_query = text("select * from store_location where state in :states").bindparams(
			bindparam('states', expanding=True)
		)
		store_df = pd.read_sql(store_query, conn, params={'states': list(STATE_SUBSET)})
		snow_df = pd.read_sql(_gen_snow_affected_sql(map_view), conn, params={'product_pn': map_view} if map_view != 'snowfall' else None)
		snow_df = snow_df.merge(store_df, on='store_id', how='left')
		store_df['text'] = store_df['store_id'] + ' - ' + store_df['street'] + ' - ' + store_df['city'] + ', ' + store_df['state']
		metric_col, color_bar_title, metric_name, color_limits = '', '', '', ()
		demand_note = ''
		if map_view == 'snowfall':
			metric_col = 'depth_in'
			color_bar_title = 'Snowfall (in)'
			metric_name = 'Snow Depth'
			color_limits = ('#9ecae1', '#08306b')
			snow_df['text'] = snow_df['store_id'].astype(str) + ' - ' + snow_df['street'] + ' - ' + snow_df['city'] + ', ' + snow_df['state'] + '<br>' + metric_name + ': ' + snow_df['depth_in'].round(2).astype(str) + ' in'
		else:
			demand_note = f"Total Demand: {snow_df['amount'].sum():,.0f} units"
			metric_col = 'amount'
			color_bar_title = 'Demand (units)'
			metric_name = 'Demand'
			color_limits = ("#e1d89e", "#a0910a")
			snow_df['text'] = snow_df['store_id'].astype(str) + ' - ' + snow_df['street'] + ' - ' + snow_df['city'] + ', ' + snow_df['state'] + '<br>' + metric_name + ': ' + snow_df['amount'].round(2).astype(str) + ' units'

		traces.append(_gen_dist_center_trace(conn))

	#Remove from store_df the stores that are in snow_df to avoid double plotting
	store_df = store_df[~store_df['store_id'].isin(snow_df['store_id'])]

	traces.append(go.Scattermap(
		lat=store_df['lat'],
		lon=store_df['lon'],
		mode='markers',
		text=store_df['text'],
		hoverinfo='skip',
		marker=go.scattermap.Marker(
			size=6,
			color=MAP_STORE_GRAY,
			opacity=0.25
		),
		name='Stores'
	))

	traces.append(go.Scattermap(
		lat=snow_df['lat'],
		lon=snow_df['lon'],
		mode='markers',
		text=snow_df['text'],
		marker=go.scattermap.Marker(
			size=snow_df[metric_col],
			sizemode='area',
			sizeref=2. * snow_df[metric_col].max() / (SNOW_MAX_MARKER_PX ** 2),
			sizemin=5,
			color=snow_df[metric_col],
			colorscale=[[0, color_limits[0]], [1, color_limits[1]]],
			cmin=0,
			cmax=snow_df[metric_col].max(),
			colorbar=go.scattermap.marker.ColorBar(
				title=color_bar_title, thickness=15, len=0.5,
				x=0.01, xanchor='left', y=0.90, yanchor='top'
			)
		),
		name=metric_name
	))

	fig = go.Figure(
		data=traces,
		layout={
			'map':{
				'center':{'lat': MAP_CENTER[0], 'lon': MAP_CENTER[1]},
				'style':'carto-positron',
				'zoom': 4.8
			},
			'margin': {'t':0,'b':0, 'l':0, 'r': 0},
			'legend':{
				'orientation':'h',
				'yanchor':'top',
				'xanchor':'right',
				'y':0,
				'x':1
			}
		}
	)

	return fig, demand_note

@callback(
	Output('supply_sidebar', 'children'),
	Input('map_view_select', 'value')
)
def update_supply_sidebar(map_view: str):
	if map_view == 'snowfall':
		return html.Span('Select a part to view distribution center supply.',
			className='fst-italic text-muted')

	query = text(
		"select dc.city, dc.state, s.amount "
		"from dist_center_product_supply s "
		"join dist_center_location dc on dc.dc_id = s.dc_id "
		"where s.product_pn = :product_pn and dc.state in :states "
		"order by s.amount desc"
	).bindparams(bindparam('states', expanding=True))

	with engine.connect() as conn:
		supply_df = pd.read_sql(
			query, conn,
			params={'product_pn': map_view, 'states': list(STATE_SUBSET)}
		)

	total = supply_df['amount'].sum()
	supply_df['location'] = supply_df['city'] + ', ' + supply_df['state']
	supply_df['pct'] = supply_df['amount'] / total * 100 if total else 0

	column_defs = [
		{'headerName': 'Distribution Center', 'field': 'location', 'flex': 2},
		{'headerName': 'Amount', 'field': 'amount', 'flex': 1, 'type': 'rightAligned',
			'valueFormatter': {'function': "d3.format(',')(params.value)"}},
		{'headerName': '% of Total', 'field': 'pct', 'flex': 1, 'type': 'rightAligned',
			'valueFormatter': {'function': "d3.format('.1f')(params.value) + '%'"}},
	]

	totals_row = {'location': 'Total', 'amount': total, 'pct': 100 if total else 0}

	return AgGrid(
		id='supply_grid',
		rowData=supply_df.to_dict('records'),
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
	)

@callback(
	Output('trans_cost_sidebar', 'children'),
	Input('map_view_select', 'value')
)
def update_trans_cost_sidebar(map_view: str):
	if map_view == 'snowfall':
			return html.Span('Select a part to view unit shipping costs.',
				className='fst-italic text-muted')

	query = """select dc.city as dc_city, dc.state as dc_state, sl.store_id, sl.city as sl_city, sl.state as sl_state, ptc.cost
				from product_trans_cost ptc
				join dist_center_location dc on ptc.dc_id = dc.dc_id
				join store_location sl on ptc.store_id = sl.store_id
				join snowfall s on ptc.store_id = s.store_id
				where ptc.product_pn = :product_pn
				order by ptc.cost desc;"""

	with engine.connect() as conn:
		df = pd.read_sql(text(query), conn, params={'product_pn': map_view})
		df['dc_city_state'] = df['dc_city'] + ', ' + df['dc_state']
		df['sl_city_state'] = df['store_id'] + ' - ' + df['sl_city'] + ', ' + df['sl_state']
		df.sort_values(by=['dc_city_state', 'sl_city_state'], inplace=True)

	return AgGrid(
		id='unit_ship_cost_grid',
		rowData=df.to_dict('records'),
		defaultColDef={'sortable': True, 'resizable': True, 'filter':True},
		style={'width': '100%'},
		dashGridOptions={'theme': 'themeBalham'},
		columnSize='responsiveSizeToFit',
		columnDefs=[
			{'field': 'dc_city_state', 'headerName': 'Dist. Center'},
			{'field': 'sl_city_state', 'headerName': 'Store'},
			{'field': 'cost', 'headerName': 'Unit Cost', 'valueFormatter': {'function': GRID_D3_CURRENCY_3_DECIMAL}, 'type': 'rightAligned'}
		]

	)


@callback(
	Output('nav_tabs', 'active_tab'),
	Output('solution_tab', 'children'),
	Input('run_model_btn', 'n_clicks'),
	prevent_initial_call=True
)
def run_model(_): 
	with engine.connect() as conn:

		DC_SUPPLY_MAP = """select dcps.*
							from dist_center_product_supply dcps
							join (select dc_id from dist_center_location where state in :states) a on dcps.dc_id = a.dc_id;"""

		dc_supply_df = pd.read_sql(text(DC_SUPPLY_MAP).bindparams(
										bindparam('states', expanding=True)
									), conn, params={'states': list(STATE_SUBSET)})

		dc_ids = dc_supply_df['dc_id'].unique().tolist()
		product_pns = dc_supply_df['product_pn'].unique().tolist()
		dc_product_supply_map = dc_supply_df.set_index(['dc_id', 'product_pn'])['amount'].to_dict()

		STORE_DEMAND_SQL = """select spd.*
								from store_product_demand spd
								join snowfall s on spd.store_id = s.store_id;"""

		store_demand_df = pd.read_sql(text(STORE_DEMAND_SQL), conn)
		store_ids = store_demand_df['store_id'].unique().tolist()
		store_product_demand_map = store_demand_df.set_index(['store_id', 'product_pn'])['amount'].to_dict()

		TRANS_COST_SQL = """select ptc.* 
							from product_trans_cost ptc 
							join snowfall s on ptc.store_id = s.store_id;"""

		trans_cost_df = pd.read_sql(text(TRANS_COST_SQL), conn)
		trans_cost_map = trans_cost_df.set_index(['dc_id', 'store_id', 'product_pn'])['cost'].to_dict()

	model = solve_model(dc_ids,
			 store_ids,
			 product_pns,
			 dc_product_supply_map,
			 store_product_demand_map,
			 trans_cost_map)
	return 'solution_tab', LpResultsView(model)

@callback(
	Output('view_model_modal', 'opened'),
	Output('view_model_modal', 'children'),
	Input('view_model_btn', 'n_clicks'),
	prevent_initial_call=True
)
def view_model_modal(_):
	return True, dcc.Markdown(MODEL_MARKDOWN, mathjax=True) 

if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0')