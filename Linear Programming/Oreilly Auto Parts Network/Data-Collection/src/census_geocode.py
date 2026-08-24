import csv
import sqlite3 as sql
from typing import List


db_path = r"C:\Users\brock\Documents\SKAGGS\Consulting\Client Outreach\O'ReillyNetwork\oreilly_network.db"

def main():
    print('running main...')
    # gen_geo_census_input_csv()
    # load_geo_census_locs()
    load_manual_geo_locs()
    print('done')


def load_geo_census_locs():
    input_path = r"C:\Users\brock\Documents\SKAGGS\Consulting\Client Outreach\O'ReillyNetwork\GeocodeResults.csv"
    sql_conn = sql.connect(db_path)
    cursor = sql_conn.cursor()
    with open(input_path, 'r') as f:
        geo_reader = csv.reader(f, delimiter=',')
        for row in geo_reader:
            if 'No_Match' in row[2] or 'Tie' in row[2]:
                continue
            store_id = row[0]
            loc_splits = row[5].split(',')
            lon = float(loc_splits[0])
            lat = float(loc_splits[1])
            sql_cmd = f"update store_location set lat = {lat}, lon = {lon} where store_id = {store_id};"
            cursor.execute(sql_cmd)
        sql_conn.commit()

def load_manual_geo_locs():
    input_path = r"C:\Users\brock\Documents\SKAGGS\Consulting\Client Outreach\O'ReillyNetwork\ManualGeocodeResults.csv"
    sql_conn = sql.connect(db_path)
    cursor = sql_conn.cursor()
    with open(input_path, 'r') as f:
        csv_reader = csv.reader(f, delimiter=',')
        is_header = True
        for row in csv_reader:
            if is_header:
                is_header = False
                continue
            store_id = row[0]
            loc_splits = row[1].split(',')
            lon = float(loc_splits[1])
            lat = float(loc_splits[0])
            sql_cmd = f"update store_location set lat = {lat}, lon = {lon} where store_id = {store_id} and lat is null;"
            cursor.execute(sql_cmd)
        sql_conn.commit()

def gen_geo_census_input_csv():
    # https://geocoding.geo.census.gov/geocoder/locations/addressbatch?form
    out_path = r"C:\Users\brock\Documents\SKAGGS\Consulting\Client Outreach\O'ReillyNetwork\oreilly_store_addresses.csv"
    sql_conn = sql.connect(db_path)
    locs = _fetch_db_locs(sql_conn)
    csvs = _gen_csv_lines(locs)
    with open(out_path, 'w') as f:
        f.writelines(csvs)

def _fetch_db_locs(sql_conn) -> List[dict]:
    locs = []
    cur = sql_conn.cursor()
    res = cur.execute("select * from store_location;")
    for i in res.fetchall():
        locs.append({
            'id': i[0],
            'street': i[1],
            'city': i[2],
            'state': i[3],
            'zip': i[4]
        })
    return locs

def _gen_csv_lines(locs: List[dict]) -> List[str]:
    def cond_txt(in_txt: str) -> str:
        if in_txt is None:
            return ''
        return f'"{in_txt}"' if "," in in_txt else in_txt
    csvs = []
    for l in locs:
        csvs.append(f"{l['id']},{cond_txt(l['street'])},{cond_txt(l['city'])},{cond_txt(l['state'])},{cond_txt(l['zip'])}\n")
    return csvs



if __name__ == '__main__':
    main()