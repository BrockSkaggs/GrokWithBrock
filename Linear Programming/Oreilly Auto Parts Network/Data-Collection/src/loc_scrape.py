import datetime as dt
from scraper import LocationScraper

def main():
    print('running scrape...')
    start = dt.datetime.now()
    db_path = r"C:\Users\brock\Documents\SKAGGS\Consulting\Client Outreach\O'ReillyNetwork\oreilly_network.db"
    scraper = LocationScraper(db_path)
    # skip_cities = scraper.get_stored_cities('VA')
    skip_cities = []    
    scraper.scrape_store_locs(['Wyoming'], skip_cities=skip_cities)
    end = dt.datetime.now()
    delta = (end - start).total_seconds()/60
    print(f'DONE - Duration: {delta:.1f} min.')

if __name__ == '__main__':
    main()