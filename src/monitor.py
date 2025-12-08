import httpx
import logging
import time
import datetime
from typing import Dict, Optional

from proxies import RotatingProxyManager
from utils import (
    create_cookie_client,
    create_api_client,
    get_random_user_agent,
    random_sleeptime,
    fetch_cookies,
    fetch_search
)
from notifier import notify

from config import (BASE_URL, API_URL, 
                         SESSION_COOKIE_NAME, PROXY_ROTATE_TIME)
import state

class VintedMonitor:
    def __init__(self, proxy_list, 
                 search_params_list, 
                 API_TOKEN, 
                 USER_KEY):

        self.proxymanager = RotatingProxyManager(proxy_list)
        self.proxy_list = proxy_list
        self.search_params_list = search_params_list
        self.API_TOKEN = API_TOKEN
        self.USER_KEY = USER_KEY
        
        self.start_time = time.time()
        self.newclient_time = time.time()
        
    def refresh_clients(self):
        user_agent = get_random_user_agent()
        proxy_url = self.proxymanager.get_next_proxy()
        cookie_client = create_cookie_client(user_agent, proxy_url)
        session_cookie = fetch_cookies(cookie_client, BASE_URL, SESSION_COOKIE_NAME)
        while session_cookie == -1:
            self.proxymanager.mark_failed(proxy_url)
            user_agent = get_random_user_agent()
            proxy_url = self.proxymanager.get_next_proxy()
            cookie_client = create_cookie_client(user_agent, proxy_url)
            session_cookie = fetch_cookies(cookie_client, BASE_URL, SESSION_COOKIE_NAME)
        logging.info("Refreshed proxy: " + str(proxy_url))
        logging.info("Refreshed cookie: " + str(session_cookie))
        api_client = create_api_client(user_agent, proxy_url, session_cookie)
        self.newclient_time = time.time()
        return proxy_url, cookie_client, api_client

    def collect_existing_ids(self):
        items = []
        for firstloop in range(2):
            for s, search_params in enumerate(self.search_params_list):
                firstsearch_params = {**search_params}
                firstsearch_params["per_page"] = 10 * firstsearch_params["per_page"]
                firstsearch_params["time"] = int(time.time())
                status_code, data = fetch_search(self.api_client, API_URL, params=firstsearch_params)
                while status_code == -1:
                    self.proxymanager.mark_failed(self.curr_proxy)
                    logging.info("Refreshing clients due to failure (firstsearch)")
                    self.curr_proxy, self.cookie_client, self.api_client = self.refresh_clients()
                    status_code, data = fetch_search(self.api_client, API_URL, params=firstsearch_params)

                data = data.json()
                if firstloop == 0:
                    logging.info(f"Searchconfig {s}:")
                for i, item in enumerate(data.get("items", [])):
                    item_id, item_name, item_url = item.get("id"), item.get("title"), item.get("url")
                    items.append(item_id)
                    if i < 4 and firstloop == 0:
                        logging.info(f"ID: {item_id}, {item_name}, URL: {item_url}")
                    
                time.sleep(random_sleeptime())
        return list(set(items))

    def run(self):
        
        logging.basicConfig(
            filename=f"logs/runfrom{datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")}.log",
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )

        logging.info("Booting Vinted Monitor...")
        self.curr_proxy, self.cookie_client, self.api_client = self.refresh_clients()
        items = self.collect_existing_ids()
        time.sleep(1)
        
        logging.info("Initial items fetched:" + str(len(items)))
        logging.info("----------------------------------------------------")
        while True:
            for search_params in self.search_params_list:
                search_params["time"] = int(time.time())
                status_code, data = fetch_search(self.api_client, API_URL, params=search_params)
                while status_code == -1:
                    self.proxymanager.mark_failed(self.curr_proxy)
                    logging.info("Refreshing clients due to failure")
                    self.curr_proxy, self.cookie_client, self.api_client = self.refresh_clients()
                    status_code, data = fetch_search(self.api_client, API_URL, params=search_params)
                
                data = data.json()
                if data.get("items") is None or len(data.get("items")) == 0:
                    logging.info("No items returned from API.")

                for item in data.get("items", []):
                    item_id = item.get("id")
                    if item_id not in items:
                        items.append(item_id)
                        item_name, item_url, item_price, item_brand, item_size = item.get("title"), item.get("url"), item.get("price"), item.get("brand_title"), item.get("size_title")
                        logging.info(f"New item found: {item_id}, URL: {item_url}")
                        notify(self.API_TOKEN, self.USER_KEY, item_name, item_url, item_price, item_brand, item_size)

                if state.api_call_counter % 50 == 0:
                    logging.info(f"Total API calls made: {state.api_call_counter}, time elapsed: {int((time.time() - self.start_time) / 3600)} hours")

                if (time.time() - self.newclient_time) > PROXY_ROTATE_TIME:
                    logging.info("Refreshing clients due to time limit.")
                    self.curr_proxy, self.cookie_client, self.api_client = self.refresh_clients()
                else:
                    time.sleep(random_sleeptime())
