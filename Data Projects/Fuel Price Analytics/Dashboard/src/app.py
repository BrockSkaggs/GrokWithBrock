from dash import Dash, html, dcc, callback, Input, Output, Patch, clientside_callback, ClientsideFunction
import dash_bootstrap_components as dbc
import plotly.graph_objs as go

from aio.aio_station_card import StationCardAIO
import utils.review_util as rev_util
from  utils.data_etl import get_condition_data, address_loc_map, station_color_map

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
data_path = '/code/gas-scrape-data.csv'
df = get_condition_data(data_path)

app.layout = html.Div([
    html.Div([
        html.Div([html.H1('Fuel Price Analytics - Carthage, MO !')], className='col-12', id='dash_title')
    ], className='row'),
    html.Div([
        html.Div([
            dbc.Card(
                dbc.CardBody([
                    html.Div([
                        html.Div([
                            html.Div([
                                dbc.Card(
                                    dbc.CardBody([
                                        html.Div([
                                            dcc.Dropdown(
                                                ['Lowest Price', 'Station', 'Summary'],
                                                value='Lowest Price',
                                                id='time_series_drpdwn',
                                                style={'width':'150px'},
                                                clearable=False
                                            ),
                                            html.Div([
                                                html.Span('Fuel Type', className='mt-auto mb-auto', style={'marginRight':'10px', 'marginLeft':'15px'}),
                                                dcc.Dropdown(
                                                    ['Regular', 'Premium', 'Diesel'],
                                                    value='Regular',
                                                    id='fuel_type_drpdwn',
                                                    style={'width':'150px'},
                                                    clearable=False
                                                )
                                            ], className='d-flex', id='fuel_type_div')
                                        ], className='d-flex'),
                                        dcc.Graph(
                                            id='time_series_chart'
                                        )
                                    ])
                                )
                            ], className='col-lg-8'),
                            html.Div([
                                dbc.Card(
                                    dbc.CardBody([
                                        dcc.Graph(
                                            id='station_map',
                                            style={'height':'100%'},
                                            clear_on_unhover=True,
                                            config={
                                                'modeBarButtonsToRemove':['lasso2d', 'select2d']
                                            }
                                        ),
                                        dcc.Tooltip(id='station_map_tooltip', direction='left')
                                    ]), className='h-100'
                                )
                            ], className='col-lg-4')
                        ], className='row')
                    ], className='container-fluid')
                ])
            )
        ], className='col-12')
    ], className='row'),
    html.Div([
        html.Div([
            html.Span('Review Station', className='mt-auto mb-auto', style={'marginRight':'5px'}),
            dcc.Dropdown(
                id='station_review_drpdown',
                options=[i.split("|")[0] for i in df['StationAddress'].unique()],
                placeholder='Select Station...',
                style={'width':'260px'}
            )
        ], className='col-12 d-flex')
    ], className='row mt-2'),
    html.Div([], className='row mt-2', id='station_card_div')
], className='container-fluid')

clientside_callback(
    ClientsideFunction(namespace="clientside", function_name="make_draggable"),
    Output('station_card_div', 'data-drag'),
    Input('station_card_div', 'id')
)

clientside_callback(
    """function(timeSeries){
            if(timeSeries == "Lowest Price") return "d-none";
            return "d-flex";
        }""",
    Output('fuel_type_div', 'className'),
    Input('time_series_drpdwn', 'value')
)

@callback(
    Output('station_map', 'figure'),
    Input('dash_title', 'className')
)
def update_map(_):
    map_df = df.copy()
    map_df.drop_duplicates(subset=['Address'], inplace=True)
    map_df = map_df[['Station', 'Address', 'StationAddress']]
    map_df['Coords'] = map_df['Address'].map(address_loc_map)
    map_df['MapColor'] = map_df['Station'].map(station_color_map)
    map_df['lat'] = map_df['Coords'].apply(lambda x: x['lat'])
    map_df['lon'] = map_df['Coords'].apply(lambda x: x['lon'])
    
    traces = []
    for station in map_df['Station'].unique():
        map_dff = map_df[map_df['Station'] == station].copy()
        traces.append(go.Scattermapbox(
            lat=map_dff['lat'],
            lon=map_dff['lon'],
            mode='markers',
            text=map_dff['StationAddress'],
            marker=go.scattermapbox.Marker(
                size=12,
                color=map_dff['MapColor'].str[:7]
            ),
            hoverinfo='none',
            name=station
        ))
        
    return go.Figure(
                data=traces,
                layout={
                    'mapbox':{
                        'center':{'lat': 37.1620, 'lon': -94.3102},
                        'style':'carto-positron',
                        'zoom': 12
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

@callback(
    Output('station_map_tooltip', 'show'),
    Output('station_map_tooltip', 'bbox'),
    Output('station_map_tooltip', 'children'),
    Input('station_map', 'hoverData'),
    prevent_initial_call=True
)
def display_map_hover(hover_data):
    #Reference: https://dash.plotly.com/dash-core-components/tooltip
    if hover_data is None:
        return False, None, None
    pt = hover_data['points'][0]
    pt_text = pt['text']
    bbox = pt['bbox']

    name_street = pt_text.split('|')[0]
    text_parts = name_street.split('-')
    children= html.Div([
        html.Img(src=rev_util.get_station_image(name_street), style={'width':'100%'}),
        html.P(f'Station: {text_parts[0].strip()}\r\nAddress: {text_parts[1].strip()}')
    ], style={'width': '300px', 'white-space':'pre-wrap'})
    return True, bbox, children

@callback(
    Output('time_series_chart', 'figure'),
    Input('time_series_drpdwn', 'value'),
    Input('fuel_type_drpdwn', 'value')
)
def update_time_series(plot_type: str, fuel_type: str):
    if plot_type == 'Lowest Price':
        return rev_util.build_lowest_price_time_series_chart(df)
    if plot_type == 'Station':
        return rev_util.build_station_time_series_chart(df, fuel_type.lower())
    return rev_util.build_summary_time_series_chart(df, fuel_type.lower())

@callback(
    Output('station_card_div', 'children'),
    Input('station_review_drpdown', 'value'),
    prevent_initial_call=True
)
def gen_station_card(user_station_address: str):
    patched_div = Patch()
    dff = df[df['StationAddress'].str.startswith(user_station_address)].copy()
    new_col = html.Div([
        StationCardAIO(dff)
    ], className='col-lg-3 mt-2')

    patched_div.prepend(new_col)
    return patched_div

if __name__ == '__main__':
    # print("running main...")
    app.run(debug=True, host='0.0.0.0', port='8049', dev_tools_hot_reload=True)