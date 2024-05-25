from dash import html, clientside_callback, Input, Output, MATCH
import dash_bootstrap_components as dbc
import datetime as dt
import pandas as pd
import uuid
from utils.review_util import get_station_image

class StationCardAIO(html.Div):

    class ids:
        close_btn = lambda aio_id: {
            'component': 'StationCardAIO',
            'subcomponent': 'close_btn',
            'aio_id': aio_id
        }

        card = lambda aio_id: {
            'component': 'StationCardAIO',
            'subcomponent': 'card',
            'aio_id': aio_id
        }

    ids = ids

    def __init__(
        self,
        station_df: pd.DataFrame,
        aio_id = None
    ):
        if aio_id is None:
            aio_id = str(uuid.uuid4())

        self.df = station_df
        super().__init__(self.build_layout(aio_id))

    def build_layout(self, aio_id: str):
        scrape_time, latest_prices = self.get_latest_pricing()
        station_street = self.df['StationAddress'].iloc[0].split('|')[0].strip()

        time_note = scrape_time.strftime('%m/%d/%Y %H:%M')
        prices_note_style = {'fontWeight':'bold'}
        if(scrape_time.date() != dt.date.today()):
            prices_note_style['color'] = 'red'
            delta = (dt.date.today() - scrape_time.date()).days
            time_note += f" ({delta} days ago)"

        return dbc.Card(
            dbc.CardBody([
                html.Div([
                    html.Div([
                        html.Div([
                            html.H3(station_street),
                            html.Img(src='./assets/images/closeTile.svg', style={'marginLeft':'auto'}, id=self.ids.close_btn(aio_id))
                        ], className='col-12 d-flex')
                    ], className='row'),
                    html.Div([
                        html.Div([
                            html.Img(src=get_station_image(station_street), style={'width':'100%'})
                        ], className='col-12')
                    ], className='row'),
                    html.Div([
                        html.Div([
                            html.Span(f'Prices as of {time_note}', style=prices_note_style)
                        ], className='col-12')
                    ], className='row'),
                    html.Div([
                        html.Div([
                            html.Span(f"◼️ Regular: {latest_prices['regular']}")
                        ], className='col-4'),
                        html.Div([
                            html.Span(f"◼️ Premium: {latest_prices['premium'] if latest_prices['premium'] is not None else 'N/A'}")
                        ], className='col-4'),
                        html.Div([
                            html.Span(f"◼️ Diesel: {latest_prices['diesel'] if latest_prices['diesel'] is not None else 'N/A'}")
                        ], className='col-4'),
                    ], className='row mt-1')
                ], className='container-fluid')
            ]), id=self.ids.card(aio_id)
        )

    def get_latest_pricing(self) -> tuple:
        df_max = self.df[self.df['ScrapeTime'] == self.df['ScrapeTime'].max()].copy()
        # time_note = df_max['ScrapeTime'].iloc[0].strftime('%m/%d/%Y %H:%M')
        scrape_time = df_max['ScrapeTime'].iloc[0].to_pydatetime()
        fuel_prices = {}
        for f_type in ('regular', 'premium', 'diesel'):
            dff = df_max[df_max['FuelType'] == f_type]
            fuel_prices[f_type] = None if dff.shape[0] == 0 else dff['CondPrice'].iloc[0]
        return (scrape_time, fuel_prices)

    clientside_callback(
        """function(clicks){
                return "d-none";
            }""",
            Output(ids.card(MATCH), 'className'),
            Input(ids.close_btn(MATCH), 'n_clicks'),
            prevent_initial_call=True
    )