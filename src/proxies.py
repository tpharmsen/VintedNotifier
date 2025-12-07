import logging
import time
from itertools import cycle

class RotatingProxyManager:
    def __init__(self, proxies, cooldown=45 * 60):
        self.proxies = proxies
        self.cooldown = cooldown
        self.proxy_cycle = cycle(proxies)
        self.failed = {} 

    def _is_alive(self, proxy):
        if proxy not in self.failed:
            return True
        return time.time() >= self.failed[proxy]

    def get_next_proxy(self):
        for _ in range(len(self.proxies)):
            proxy = next(self.proxy_cycle)
            if self._is_alive(proxy):
                return proxy
                #return {
                #    "http://": proxy,
                #    "https://": proxy,
                #}
        logging.info("⚠️⚠️⚠️ All proxies are in cooldown.")
        raise RuntimeError("All proxies are in cooldown — no proxy available")

    def mark_failed(self, proxy):
        
        logging.info(f"Marking proxy: {proxy} as down for assumed {int(self.cooldown / 60)} min.")
        self.failed[proxy] = time.time() + self.cooldown
