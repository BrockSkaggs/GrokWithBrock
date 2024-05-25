import datetime as dt
import pandas as pd

start_date = dt.date(2024, 4, 2)

def get_data(data_path: str) -> pd.DataFrame:
    col_names = ['ScrapeTime','CardPos','FuelType','Station','Address','RawPrice','CondPrice']
    df = pd.read_csv(data_path, names=col_names, parse_dates=['ScrapeTime'])
    df['ScrapeDate'] = df['ScrapeTime'].dt.date
    df['StationAddress'] = df['Station'] + ' - ' + df['Address']
    return df[(~df['CondPrice'].isna()) & (df['ScrapeDate'] >= start_date)].copy()

def condition_data(df: pd.DataFrame):
    dates = df['ScrapeDate'].unique()
    fuel_types = df['FuelType'].unique()
    cond_pos = {}
    price_delta = {}
    for date in dates:
        for f_type in fuel_types:
            dff = df[(df['ScrapeDate'] == date) & (df['FuelType'] == f_type)].copy()
            min_pos = dff['CardPos'].min()
            min_price = dff['CondPrice'].min()
            f_type_cond_pos = dff['CardPos'] - min_pos
            f_type_delta_price = dff['CondPrice'] - min_price
            cond_pos.update(f_type_cond_pos)
            price_delta.update(f_type_delta_price)
    df['CondCardPos'] = df.index.map(cond_pos)
    df['PriceDelta'] = df.index.map(price_delta)
    
def get_condition_data(data_path: str) -> pd.DataFrame:
    df = get_data(data_path)
    condition_data(df)
    return df

address_loc_map = {
	"13011 MO-96|Carthage, MO": {"lat": 37.19162631697573, "lon": -94.29238301538633},
	"824 E Fairview Ave|Carthage, MO": {"lat": 37.15446846025172, "lon": -94.30140681439775},
	"410 S Garrison Ave|Carthage, MO": {"lat": 37.175530401792486, "lon": -94.31385361898413},
	"201 E Central Ave|Carthage, MO": {"lat": 37.17892554804995, "lon": -94.30868390723654},
	"301 W Central Ave|Carthage, MO": {"lat": 37.178792451426496, "lon": -94.31271891860102},
	"2635 Grand Ave|Carthage, MO": {"lat": 37.14267360328203, "lon": -94.3111907640555},
	"917 W Central Ave|Carthage, MO": {"lat": 37.17919329341171, "lon": -94.32248942184653},
	"2214 Fairlawn Ave|Carthage, MO": {"lat": 37.15071324511616, "lon": -94.31391117101225},
	"1224 W Central Ave|Carthage, MO": {"lat": 37.17860846480153, "lon": -94.32716332866889},
	"2812 Hazel St|Carthage, MO": {"lat": 37.13960681105043, "lon": -94.31949396812074}
}

station_color_map = {
    'Murphy USA': '#0215e6',
    'Phillips 66': '#e60202',
    "Casey's": '#e66502s',
    'Flyin W': '#666666',
    'The Corner': '#e3e300'
}
