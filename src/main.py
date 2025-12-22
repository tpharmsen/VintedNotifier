import os
import sys
import time
import logging

from monitor import VintedMonitor
from notifier import notify
from utils import load_yaml, load_txt_lines, scrape_and_save_proxies

from dotenv import load_dotenv
load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
USER_KEY = os.getenv("USER_KEY")

if not API_TOKEN or not USER_KEY:
    raise ValueError("API_TOKEN and USER_KEY must be set in the .env file.")

if not os.path.exists("logs"):
    os.makedirs("logs")

maxnum = 10

def create_monitor():
    # proxy list
    if len(sys.argv) > 1 and sys.argv[1].endswith(".txt"):
        proxy_list = load_txt_lines(sys.argv[1])
    else:
        scrape_and_save_proxies()
        proxy_list = load_txt_lines("proxy_list.txt")

    if not proxy_list:
        raise ValueError("proxy_list.txt is empty or could not be loaded.")
    elif len(proxy_list) < 10:
        print(f"Warning: proxy_list.txt contains only {len(proxy_list)} proxies")

    # search params
    config = load_yaml("search_params.yaml")
    search_params_list = config.get("search_params")
    if search_params_list is None:
        raise KeyError("search_params.yaml must contain a 'search_params' key.")
    
    return VintedMonitor(proxy_list, search_params_list, API_TOKEN, USER_KEY)

def close_logger(logger):
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


if __name__ == "__main__":
    print("""
          ***
          Warning! Vinted Terms of Service forbids scraping or automated tools.
          Usage may result in a permanent ban.
          ***
    """)
    for num in range(1, maxnum + 1):
        monitor = None
        try:
            monitor = create_monitor()
            monitor.run()

        except Exception as e:
            monitor.logger.exception(f"{num}/{maxnum}| Exception occurred")
            monitor.logger.error(f"{num}/{maxnum}| Vinted notifier crashed: {e}")
            notify(monitor.logger, f"{num}/{maxnum} | Vinted notifier crashed: {e}", API_TOKEN, USER_KEY)

            if monitor is not None and hasattr(monitor, "logger"):
                close_logger(monitor.logger)

            print(f"{num}/{maxnum}| Main loop error occurred: {e}, restarting in 60 seconds...")
            time.sleep(60)
            continue
