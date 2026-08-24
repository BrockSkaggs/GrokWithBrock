import json
import sqlite3 as sql

db_path = r"C:\Users\brock\Documents\SKAGGS\Consulting\Client Outreach\O'ReillyNetwork\Dashboard\data\oreilly_network.db"
dc_src_path = r"C:\Users\brock\Documents\SKAGGS\Consulting\Client Outreach\O'ReillyNetwork\distribution_centers.json"

def main():
    print('running main...')

    dc_dets = []
    with open(dc_src_path, 'r') as f:
        dc_dets = json.load(f)

    conn = sql.connect(db_path)
    cur = conn.cursor()
    for dc_det in dc_dets:
        insert = f"INSERT INTO dist_center_location VALUES (NULL, '{dc_det['street']}', '{dc_det['city']}', '{dc_det['state']}', '{dc_det['zip']}', {dc_det['lat']}, {dc_det['lon']})"
        cur.execute(insert)
    conn.commit()

    print('done!')



if __name__ == '__main__':
    main()