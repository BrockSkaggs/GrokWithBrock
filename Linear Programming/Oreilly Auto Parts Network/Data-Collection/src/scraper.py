import re
from selenium import webdriver
from selenium.webdriver.common.by import By
import sqlite3 as sql
from typing import Optional, List

class LocationScraper:
    
    loc_home_url = 'https://locations.oreillyauto.com/'

    def __init__(self, db_path:Optional[str]=None):
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(5)
        self.store_addresses = []
        self.sql_conn = None
        self.stored_ids = []
        if db_path is not None:
            self.sql_conn = sql.connect(db_path)

    def scrape_store_locs(self, state_subset: List[str] = [], **kwargs):
        self._get_home_url()
        state_anchors = self._get_ul_content()
        if len(state_subset) > 0:
            state_anchors = [s for s in state_anchors if any(t in s.text for t in state_subset)]
            self.stored_ids = self._get_stored_store_ids()

        for state_anchor in state_anchors:
            self._check_feedback_modal()
            state_anchor.click()
            self._scrape_state_page(**kwargs)
            self._get_home_url()
            self._check_feedback_modal()

    def _scrape_state_page(self, **kwargs):
        city_anchors = self._get_ul_content()
        skip_cities = [] if 'skip_cities' not in kwargs.keys() else kwargs['skip_cities']
        for city_anchor in city_anchors:
            if any(c in city_anchor.text for c in skip_cities):
                continue
            self._check_feedback_modal()
            store_qty = self._check_store_qty(city_anchor.text)
            city_anchor.click()
            self._scrape_city_page(store_qty > 1)
            self.driver.back()
            self._check_feedback_modal()
    
    def _scrape_city_page(self, multi_store: bool):
        self._check_feedback_modal()
        if multi_store:
            content = self.driver.find_element(By.ID, 'browse-content')
            card_bodies = content.find_elements(By.CLASS_NAME, 'map-list-item')
            for body in card_bodies:
                body_content = body.find_element(By.CLASS_NAME, 'map-list-content')         
                header_div = body_content.find_element(By.CLASS_NAME, 'map-list-store')
                store_num_span = header_div.find_element(By.TAG_NAME, 'span')
                store_id = store_num_span.text.lower().replace('store','').strip()
                address_div = body_content.find_element(By.CLASS_NAME, 'address')
                self._parse_address_text(address_div.text, store_id)
        else:
            cards = self.driver.find_elements(By.CLASS_NAME, 'indy-card-content')
            loc_div = cards[0].find_element(By.CLASS_NAME,'location-details')
            info_span = loc_div.find_element(By.CLASS_NAME, 'info')
            store_num_span = loc_div.find_element(By.CLASS_NAME,'store-number')
            store_id = store_num_span.text.split('#')[1].strip()
            self._parse_address_text(info_span.text, store_id)

    def _get_ul_content(self):
        content_div_ul = self.driver.find_element(By.ID, 'browse-content')
        content_li_list = content_div_ul.find_elements(By.TAG_NAME, 'li')
        content_anchors = [li.find_element(By.TAG_NAME, 'a') for li in content_li_list]
        return content_anchors

    def _check_feedback_modal(self):
        try:
            modal = self.driver.find_element(By.CLASS_NAME, 'uws-modal')
        except Exception as e:
            return
        for modal_btn in modal.find_elements(By.CLASS_NAME,'uws-button'):
            if not modal_btn.text.startswith('no'):
                continue
            modal_btn.click()

    def _check_store_qty(self, desc: str) -> int:
        reg_match = re.search(r'\(\d+\)$', desc)
        if reg_match is None:
            return 1
        return int(desc[reg_match.span()[0]:].replace('(','').replace(')', ''))

    def _parse_address_text(self, text:str, store_id: str):
        address_parts = text.split("\n")
        city_state = address_parts[1].split(',')
        raw_state = city_state[1].strip()
        state_parts = raw_state.split(' ')
        zip_code = None if len(state_parts) == 1 else state_parts[1].strip()
        street = address_parts[0].strip()
        city = city_state[0].strip()
        state = state_parts[0].strip()

        if self.sql_conn is not None and store_id not in self.stored_ids:
            self._address_insert(store_id, street, city, state, zip_code)

        self.store_addresses.append({
            'store_id': store_id,
            'street': street,
            'city': city,
            'state': state,
            'zip': zip_code
        })

    def _address_insert(self, store_id: str, street: str, city: str, state: str, zip: str):
        def cond_text(text: str) -> str:
            return text.replace("'", "''")

        cur = self.sql_conn.cursor()
        zip_clause = 'null' if zip is None else f"'{cond_text(zip)}'"
        sql = f"""INSERT INTO store_location VALUES (
            '{store_id}', '{cond_text(street)}', '{cond_text(city)}', '{cond_text(state)}', {zip_clause}, null, null)"""
        cur.execute(sql)
        self.sql_conn.commit()

    def _get_home_url(self):
        self.driver.get(self.loc_home_url)

    def _get_stored_store_ids(self):
        cur = self.sql_conn.cursor()
        res = cur.execute("select store_id from store_location;")
        return [i[0] for i in res.fetchall()] 

    def get_stored_cities(self, state_code: str):
        if self.sql_conn is None:
            return []
        cur = self.sql_conn.cursor()
        res = cur.execute(f"select city from store_location where state = '{state_code}';")
        return [i[0] for i in res.fetchall()]
