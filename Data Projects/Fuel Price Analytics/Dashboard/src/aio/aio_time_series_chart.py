from dash import html, dcc
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go
import uuid

class TimeSeriesChartAIO(html.Div):

    class ids:
        drpdwn = lambda aio_id: {
            'component': 'TimeSeriesChartAIO',
            'subcomponent': 'drpdwn',
            'aio_id': aio_id
        }

        time_series_chart = lambda aio_id: {
            'component': 'TimeSeriesChartAIO',
            'subcomponent': 'time_series_chart',
            'aio_id': aio_id
        }

        fuel_price_store = lambda aio_id: {
            'component': 'TimeSeriesChartAIO',
            'subcomponent': 'fuel_price_store',
            'aio_id': aio_id
        }

        

    ids = ids

    def __init__(
        self,
        fuel_df: pd.DataFrame,
        aio_id = None
    ):
        if aio_id is None:
            aio_id = str(uuid.uuid4())

        super().__init__(self.build_layout(fuel_df, aio_id))

    
    def build_layout(self, fuel_df: pd.DataFrame, aio_id: str):
        return dbc.Card(
            dbc.CardBody([
                html.Div([
                    html.Div([
                        html.Div([
                            dcc.Dropdown(
                                ['Lowest Price', 'Station', 'Summary'],
                                value='Lowest Price',
                                id=self.ids.drpdwn(aio_id),
                                style={'width':'150px'},
                                clearable=False
                            ),
                            dcc.Graph(
                                id=self.ids.time_series_chart(aio_id)
                            )                
                        ], className='col-12'),
                    ], className='row'),
                    dcc.Store(data=fuel_df.to_dict('records'), id=self.ids.fuel_price_store(aio_id))
                ], className='container-fluid')
            ])
        )     