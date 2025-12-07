import httpx
import logging
import random
import time
from typing import Dict, Optional
import yaml

from config import (UA_LIST, BASE_HEADERS, 
                         SESSION_COOKIE_NAME, SLEEPTIME_MIN, 
                         SLEEPTIME_MAX, SLEEPTIME_LONG)
import state

def load_yaml(path: str):
    """Load a YAML file and return the parsed Python object."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)    

def load_txt_lines(path: str):
    """Load a TXT file and return a list of non-empty stripped lines."""
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def create_cookie_client(user_agent, proxy_url=None):
    return httpx.Client(
        headers={
            **BASE_HEADERS,
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            #"Sec-Fetch-Site": "none",
            #"Sec-Fetch-Mode": "navigate",
            #"Sec-Fetch-Dest": "document",
        },
        proxy=proxy_url,
        timeout=40,
        follow_redirects=True
    )

def create_api_client(user_agent, proxy_url, session_cookie):
    return httpx.Client(
        headers={
            **BASE_HEADERS,
            "User-Agent": user_agent,
            "Accept": "application/json, text/plain, */*",
            "Cookie": f"{SESSION_COOKIE_NAME}={session_cookie}",
            #"Connection": "keep-alive",
            #"Sec-Fetch-Site": "same-origin",
            #"Sec-Fetch-Mode": "cors",
            #"Sec-Fetch-Dest": "empty",
        }, 
        proxy=proxy_url,
        timeout=40,
        follow_redirects=True
    )


def get_random_user_agent() -> str:
    return random.choice(UA_LIST)["ua"]

def random_sleeptime():
    return random.randint(SLEEPTIME_MIN, SLEEPTIME_MAX)

def fetch_cookies(client: httpx.Client, url: str, cookie_name: str, tries: int = 2) -> str:
    for attempt in range(tries):
        try:
            response = client.get(url)
            state.api_call_counter += 1
            if response.status_code != 200:
                logging.info("Response status cookie fetch:" + str(response.status_code))
            cookie = response.cookies.get(cookie_name)
            if cookie is not None:
                return cookie
        except httpx.TimeoutException as e:
            logging.info(f"Timeout during cookie fetch attempt: {e}")
        except httpx.RequestError as e:
            logging.info(f"RequestError during cookie fetch attempt: {e}")
        
        if attempt < tries - 1:
            time.sleep(random_sleeptime() * (1 + attempt)) 
    logging.info(f"Failed to retrieve cookie '{cookie_name}' after {tries} tries.")
    return -1

def fetch_search(client: httpx.Client, url: str, params: Optional[Dict] = None, tries = 2):
    for attempt in range(tries):
        try:
            response = client.get(url, params=params)
            state.api_call_counter += 1
            if response.status_code == 200:
                return response.status_code, response
            elif response.status_code == 429:
                logging.info("429; Too Many Requests -> Sleeping...")
                time.sleep(SLEEPTIME_LONG)
                return response.status_code, response
            else:
                logging.info(str(response.status_code) + " during API call")
        except httpx.TimeoutException:
            logging.info("Timeout during API call")
        except httpx.RequestError as e:
            logging.info(f"RequestError during API call: {e}")
        if attempt < tries - 1:
            time.sleep(random_sleeptime())
    logging.info(f"Failed to fetch search after {tries} tries.")
    return -1, None

def get_iteminfo(html: str):
    items = None
    return items

