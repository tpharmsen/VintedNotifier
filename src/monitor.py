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
                         SESSION_COOKIE_NAME, PROXY_ROTATE_TIME, TRIES)
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

        self.logger = logging.getLogger("VintedMonitor")
        self.logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(f"logs/logfrom{datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")}.log")
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        self.logger.propagate = False
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        self.latest_request = None
    
    def log_request(self, request: httpx.Request):
        self.latest_request = {
            "method": request.method,
            "url": str(request.url),
            "start": time.time(),
        }

    def log_response(self, response: httpx.Response):
        if self.latest_request is None:
            return 
        duration = time.time() - self.latest_request["start"]
        self.logger.info(
            f'"{response.http_version.upper()} {response.status_code} {response.reason_phrase}" | '
            f'{duration:.2f}s | '
            f'{self.latest_request["method"]} {self.latest_request["url"]}'
            )
        self.latest_request = None 
    """
    # HTTPX request hook
    def log_request(self, request):
        self.logger.info(f"HTTP Request: {request.method} {request.url}")

    # HTTPX response hook
    def log_response(self, response):
        self.logger.info(f'HTTP Response: "{response.http_version.upper()} {response.status_code} {response.reason_phrase}"')
    """

    def refresh_clients(self):
        user_agent = get_random_user_agent()
        proxy_url = self.proxymanager.get_next_proxy()
        cookie_client = create_cookie_client(user_agent, proxy_url, 
                                             request_hooks=[self.log_request],
                                             response_hooks=[self.log_response])
        session_cookie = fetch_cookies(cookie_client, BASE_URL, SESSION_COOKIE_NAME, tries=TRIES, logger=self.logger)
        while session_cookie == -1:
            self.logger.info(f"Marking proxy: {proxy_url} as down for assumed {int(self.proxymanager.cooldown / 60)} min.")
            self.proxymanager.mark_failed(proxy_url)
            user_agent = get_random_user_agent()
            proxy_url = self.proxymanager.get_next_proxy()
            cookie_client = create_cookie_client(user_agent, proxy_url, 
                                                 request_hooks=[self.log_request],
                                                 response_hooks=[self.log_response])
            session_cookie = fetch_cookies(cookie_client, BASE_URL, SESSION_COOKIE_NAME, tries=TRIES, logger=self.logger)
        self.logger.info("Refreshed proxy: " + str(proxy_url) + " with cookie: ..." + str(session_cookie)[:20])
        api_client = create_api_client(user_agent, proxy_url, session_cookie,
                                       request_hooks=[self.log_request],
                                       response_hooks=[self.log_response])
        self.newclient_time = time.time()
        return proxy_url, cookie_client, api_client

    def collect_existing_ids(self):
        items = []
        for firstloop in range(2):
            for s, search_params in enumerate(self.search_params_list):
                firstsearch_params = {**search_params}
                firstsearch_params["per_page"] = 10 * firstsearch_params["per_page"]
                firstsearch_params["time"] = int(time.time())
                status_code, data = fetch_search(self.api_client, API_URL, params=firstsearch_params, tries=TRIES, logger=self.logger)
                while status_code == -1:
                    self.logger.info(f"Marking proxy: {self.curr_proxy} as down for assumed {int(self.proxymanager.cooldown / 60)} min.")
                    self.proxymanager.mark_failed(self.curr_proxy)
                    self.logger.info("Refreshing clients due to failure (firstsearch)")
                    self.curr_proxy, self.cookie_client, self.api_client = self.refresh_clients()
                    status_code, data = fetch_search(self.api_client, API_URL, params=firstsearch_params, tries=TRIES, logger=self.logger)

                data = data.json()
                if firstloop == 0:
                    self.logger.info(f"Searchconfig {s}:")
                for i, item in enumerate(data.get("items", [])):
                    item_id, item_name, item_url = item.get("id"), item.get("title"), item.get("url")
                    items.append(item_id)
                    if i < 4 and firstloop == 0:
                        self.logger.info(f"ID: {item_id}, {item_name}, URL: {item_url}")
                time.sleep(int(random_sleeptime()) / 2)
        return list(set(items))

    def run(self):
        self.logger.info("Booting Vinted Monitor...")
        print("Vinted Monitor started...")
        notify(self.logger, "Vinted Monitor started...", self.API_TOKEN, self.USER_KEY)
                
        self.curr_proxy, self.cookie_client, self.api_client = self.refresh_clients()
        items = self.collect_existing_ids()
        #raise ValueError("Debugging - stop after first search")
        
        self.logger.info("Initial items fetched:" + str(len(items)))
        print("Initial items fetched:" + str(len(items)))
        self.logger.info("----------------------------------------------------")
        print("----------------------------------------------------")
        while True:
            for search_params in self.search_params_list:
                search_params["time"] = int(time.time())
                status_code, data = fetch_search(self.api_client, API_URL, params=search_params, tries=TRIES, logger=self.logger)
                while status_code == -1:
                    self.logger.info(f"Marking proxy: {self.curr_proxy} as down for assumed {int(self.proxymanager.cooldown / 60)} min.")
                    self.proxymanager.mark_failed(self.curr_proxy)
                    self.logger.info("Refreshing clients due to failure")
                    self.curr_proxy, self.cookie_client, self.api_client = self.refresh_clients()
                    status_code, data = fetch_search(self.api_client, API_URL, params=search_params, tries=TRIES, logger=self.logger)
                
                data = data.json()
                if data.get("items") is None or len(data.get("items")) == 0:
                    self.logger.info("No items returned from API.")

                for item in data.get("items", []):
                    item_id = item.get("id")
                    if item_id not in items:
                        items.append(item_id)
                        item_name, item_url, item_price, item_brand, item_size = item.get("title"), item.get("url"), item.get("price"), item.get("brand_title"), item.get("size_title")
                        self.logger.info(f"New item found: {item_id}, URL: {item_url}")
                        message = f"{item_name}\nPrice: {item_price['amount']} {item_price['currency_code']}\nBrand: {item_brand}\nSize: {item_size}\nURL: {item_url}"
                        notify(self.logger, message, self.API_TOKEN, self.USER_KEY)

                if state.api_call_counter % 50 == 0:
                    elapsed_string = f"Total API calls made: {state.api_call_counter}, time elapsed: {int((time.time() - self.start_time) / 3600)} hours"
                    self.logger.info(elapsed_string)
                    print(elapsed_string)
                if (time.time() - self.newclient_time) > PROXY_ROTATE_TIME:
                    self.logger.info("Refreshing clients due to time limit.")
                    self.curr_proxy, self.cookie_client, self.api_client = self.refresh_clients()
                else:
                    time.sleep(random_sleeptime())
