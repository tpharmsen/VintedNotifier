import os
import sys
import time
from monitor import VintedMonitor
from notifier import send_error_notification
from utils import load_yaml, load_txt_lines, scrape_and_save_proxies

from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
USER_KEY = os.getenv("USER_KEY")

if not API_TOKEN or not USER_KEY:
    raise ValueError("API_TOKEN and USER_KEY must be set in the .env file.")

def main():
    # read name of proxylist file from arguments
    if sys.argv == "*.txt":
        proxy_list = load_txt_lines(sys.argv[1])
    else:
        scrape_and_save_proxies()
        proxy_list = load_txt_lines("proxy_list.txt")
    
    config = load_yaml("search_params.yaml")

    search_params_list = config.get("search_params")
    if search_params_list is None:
        raise KeyError("search_params.yaml must contain a 'search_params' key.")
    
    if proxy_list is None or len(proxy_list) == 0:
        raise ValueError("proxy_list.txt is empty or could not be loaded.")
    elif len(proxy_list) < 10:
        print("Warning: proxy_list.txt contains less than 10 proxies")

    if not os.path.exists("logs"):
        os.makedirs("logs")

    monitor = VintedMonitor(proxy_list, search_params_list, API_TOKEN, USER_KEY)
    try:
        monitor.run()
    except Exception as e:
        print(f"Main error occured: {e}")

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            send_error_notification(API_TOKEN, USER_KEY, f"Vinted notifier crashed: {e}")
            print(f"Main loop error occured: {e}, restarting in 60 seconds...")
            time.sleep(60)      
            continue
