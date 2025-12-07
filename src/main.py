import os
from monitor import VintedMonitor
from utils import load_yaml, load_txt_lines
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
USER_KEY = os.getenv("USER_KEY")

if not API_TOKEN or not USER_KEY:
    raise ValueError("API_TOKEN and USER_KEY must be set in the .env file.")

def main():
    proxy_list = load_txt_lines("proxy_list.txt")
    config = load_yaml("search_params.yaml")

    # safer: fails loudly if key missing
    search_params_list = config.get("search_params")
    if search_params_list is None:
        raise KeyError("search_params.yaml must contain a 'search_params' key.")
    
    if proxy_list is None or len(proxy_list) == 0:
        raise ValueError("proxy_list.txt is empty or could not be loaded.")

    if not os.path.exists("logs"):
        os.makedirs("logs")

    monitor = VintedMonitor(proxy_list, search_params_list, API_TOKEN, USER_KEY)
    monitor.run()

if __name__ == "__main__":
    main()
