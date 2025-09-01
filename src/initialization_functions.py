import random
import re

from Logger import logger
from Queues import PROXY_QUEUE
from concurrent.futures import ThreadPoolExecutor, as_completed
import os, requests, time

from Config import CONFIG



def load_tokens():
    try:
        tokens_path = os.path.join(os.path.dirname(__file__), "..", "input", "tokens.txt")
        tokens_path = os.path.abspath(tokens_path)

        with open(tokens_path, "r") as f:
            TOKENS = [line.strip() for line in f if line.strip()]

            if CONFIG["UseMultipleThreadsForTokenCheck"]:
                logger.info("Using multiple threads to check tokens.")
                with ThreadPoolExecutor(max_workers=CONFIG["MaxThreadsForTokenCheck"]) as executor:
                    futures = {executor.submit(check_token, token): token for token in TOKENS}

                    for future in as_completed(futures):
                        token = futures[future]
                        try:
                            result = future.result()
                            if not result:
                                TOKENS.remove(token)
                        except Exception as e:
                            logger.err(f"Error in checking token using multiple threads: {e}")
            else:
                for token in TOKENS:
                    result = check_token(token)
                    if not result:
                        TOKENS.remove(token)
        return TOKENS
    except Exception as e:
        logger.err(f"Failed to load tokens. {e}")

def load_proxys():
    try:
        proxys_path = os.path.join(os.path.dirname(__file__), "..", "input", "proxys.txt")
        proxys_path = os.path.abspath(proxys_path)

        with open(proxys_path, "r") as f:
            PROXYS = [line.strip() for line in f if line.strip()]
            if CONFIG["UseMultipleThreadsForProxyCheck"]:
                logger.info("Using multiple threads to check proxys.")
                with ThreadPoolExecutor(max_workers=CONFIG["MaxThreadsForProxyCheck"]) as executor:
                    futures = {executor.submit(test_proxy, proxy): proxy for proxy in PROXYS}

                    for future in as_completed(futures):
                        proxy = futures[future]
                        try:
                            result = future.result()
                            if not result:
                                PROXYS.remove(proxy)
                        except Exception as e:
                            logger.err(f"Error testing the proxy {proxy} using multiple threads. Error: {e}")
            else:
                for proxy in PROXYS:
                    result = test_proxy(proxy)
                    if not result:
                        PROXYS.remove(proxy)

        return PROXYS
    except Exception as e:
        logger.err(f"Failed to load proxys. {e}")

def test_proxy(proxy, max_retries=CONFIG["MaxRetriesForFailedRequests"], delay=CONFIG["DelayBetweenFailedRequests"]):
    proxies = {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}",
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=10)
            if response.status_code == 200:
                logger.suc(f"The proxy: {proxy} is working! {response.json()}")
                return True
            else:
                logger.err(f"The proxy: {proxy} isn't working. {response.json()}")
                return False

        except Exception as e:
            logger.err(f"Attempt {attempt}:  Read timeout: {e}")
            if attempt < max_retries:
                time.sleep(delay)  # wait before retrying
            else:
                return False

def grab_proxy():
    proxy = PROXY_QUEUE.get()
    PROXY_QUEUE.put(proxy)
    return proxy


def check_token(token, max_retries=CONFIG["MaxRetriesForFailedRequests"], delay=CONFIG["DelayBetweenFailedRequests"]):
    url = "https://discord.com/api/v10/users/@me"

    proxy = PROXY_QUEUE.get()
    PROXY_QUEUE.put(proxy)
    proxies = {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}",
    }

    headers = {"Authorization": token}

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=headers, proxies=proxies, timeout=10)
            if response.status_code == 200:
                logger.suc(f"The token ending in [...{token[-5:]}] is valid!")
                return True
            elif response.status_code == 401:
                logger.info(f"The token ending in [...{token[-5:]}] is invalid or has expired.")
                return False
            else:
                logger.info(f"Unexpected token status [{response.status_code}] for token [...{token[-5:]}]")
                return False

        except requests.exceptions.RequestException as e:
            logger.err(f"Attempt {attempt}: Error connecting for token [...{token[-5:]}]: {e}")
            if attempt < max_retries:
                time.sleep(delay)  # wait before retrying
            else:
                return False

def parse_time_range(time_range_str):
    """
    Converts a time range like "2m-5m" or "30m-1h" into a random number of seconds.
    """
    def time_to_seconds(t):
        """Convert '2m', '1h', '30s' to seconds."""
        num = int(re.findall(r'\d+', t)[0])
        if 'h' in t:
            return num * 3600
        elif 'm' in t:
            return num * 60
        elif 's' in t:
            return num
        else:
            return num  # fallback, assume seconds if no unit

    try:
        start_str, end_str = time_range_str.split('-')
        start_sec = time_to_seconds(start_str)
        end_sec = time_to_seconds(end_str)
        return random.randint(start_sec, end_sec)
    except Exception as e:
        print(f"Error parsing time range '{time_range_str}': {e}")
        return 0
