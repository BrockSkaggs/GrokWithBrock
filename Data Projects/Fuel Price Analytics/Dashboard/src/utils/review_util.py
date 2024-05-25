import base64
import io
from os import path
import pandas as pd
from PIL import Image
import plotly.graph_objects as go

def get_time_series_by_type_pos(df: pd.DataFrame, fuel_type: str, cond_pos=0) -> go.Scatter:
    dff = df[(df['FuelType'] == fuel_type) & (df['CondCardPos'] == 0)].copy()
    hover = '<b>Date: </b>' + dff['ScrapeTime'].dt.strftime('%m/%d/%Y') + '<br>' + '<b>Cost: </b>' + dff.RawPrice.astype(str) + \
        '<br>' + '<b>Station: </b>' + dff['Station'] + '<br>' + '<b>Address: </b>' + dff['Address'].str.replace('|','<br>', regex=False)
    dff['ScrapeTime'] = dff['ScrapeTime'].dt.date
    dff.set_index('ScrapeTime', inplace=True)
    return go.Scatter(
        x=dff.index,
        y=dff['CondPrice'],
        name=fuel_type,
        hovertemplate=hover
    )

def build_lowest_price_time_series_chart(df: pd.DataFrame) -> go.Figure:
    traces = []
    for fuel_type in df['FuelType'].unique():
        traces.append(get_time_series_by_type_pos(df, fuel_type))

    layout = {
        # 'height':600,
        #'yaxis': {'range':[3,4.2], 'dtick': 0.1},
        'title': {'text':'Lowest Fuel Prices in Carthage, MO'}
    }
        
    return go.Figure(data=traces, layout=layout)

def get_data_by_fuel_type_address(df: pd.DataFrame, fuel_type: str, address: str) -> pd.DataFrame:
    return df[(df['FuelType'] == fuel_type) & (df['Address'] == address)].copy()
    
def get_time_series_by_fuel_type_address(df: pd.DataFrame, fuel_type: str, address: str) -> pd.DataFrame:
    dff = get_data_by_fuel_type_address(df, fuel_type, address)
    if dff.shape[0] == 0:
        return None
    
    dff['ScrapeTime'] = dff['ScrapeTime'].dt.date
    dff.set_index('ScrapeTime', inplace=True)
    return go.Scatter(
        x = dff.index,
        y = dff['CondPrice'],
        name=dff['StationAddress'].iloc[0].split('|')[0]
    )

def build_station_time_series_chart(df: pd.DataFrame, fuel_type: str) -> go.Figure:
    def build_fuel_type_station_traces(fuel_type: str) -> list:
        station_traces = []
        for address in df['Address'].unique():
            trace = get_time_series_by_fuel_type_address(df,fuel_type, address)
            if trace is None:
                continue
            station_traces.append(trace)
        return station_traces

    station_traces = build_fuel_type_station_traces(fuel_type)

    layout = {
        # 'height':600,
        #'yaxis': {'range':[3,4.2], 'dtick': 0.1},
        'title': {'text':'Fuel Price Time Series by Station'},
        'hovermode':'x'
    }
        
    return go.Figure(data=station_traces, layout=layout)

def compute_summary_time_series(df: pd.DataFrame, fuel_type: str) -> list:
    dff = df[df['FuelType'] == fuel_type].copy()
    dff['ScrapeTime'] = dff['ScrapeTime'].dt.date
    mean_price = dff.groupby('ScrapeTime')['CondPrice'].mean()
    max_price = dff.groupby('ScrapeTime')['CondPrice'].max()
    min_price = dff.groupby('ScrapeTime')['CondPrice'].min()
    traces = []
    traces.append(go.Scatter(x=mean_price.index, y=mean_price.values,name='Average', line_dash='dash', line_color='gray'))
    traces.append(go.Scatter(x=max_price.index, y=max_price.values,name='Max'))
    traces.append(go.Scatter(x=min_price.index, y=min_price.values,name='Min', fill='tonexty', line_color='blue'))
    return traces

def build_summary_time_series_chart(df: pd.DataFrame, fuel_type: str) -> go.Figure:
    traces = compute_summary_time_series(df, fuel_type)
    layout = {
        'height':500,
        'title': {'text':'Summary Time Series'},
        'hovermode':'x'
    }
    return go.Figure(data=traces, layout=layout)

def get_station_image(station_address: str):
    img_dir = './src/assets/images/'
    img_path = path.join(img_dir, f"{station_address}.jpg")
    if not path.exists(img_path):
        img_path = './src/assets/images/test-img.jpg'
    im = Image.open(img_path)
    buffer = io.BytesIO()
    im.save(buffer, format="jpeg")
    encoded_image = base64.b64encode(buffer.getvalue()).decode()
    im_url = "data:image/jpeg;base64, " + encoded_image
    return im_url