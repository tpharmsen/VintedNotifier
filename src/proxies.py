import logging
import time
from itertools import cycle
from config import PROXY_COOLDOWN

class RotatingProxyManager:
    def __init__(self, proxies, cooldown=PROXY_COOLDOWN):
        self.proxies = proxies
        self.cooldown = cooldown
        self.proxy_cycle = cycle(proxies)
        self.failed = {} 
        # dead initialisation
        #for proxy in proxies:
        #    self.failed[proxy] = time.time() - self.cooldown * 10 # 


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
        raise RuntimeError("All proxies are in cooldown — no proxy available")

    def mark_failed(self, proxy):
        self.failed[proxy] = time.time() + self.cooldown
