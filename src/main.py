from Logger import logger
from initialization_functions import load_tokens, load_proxys
from flow import threaded_server_spam
from Config import CONFIG
from Queues import PROXY_QUEUE, TOKEN_QUEUE
import sys, threading, io


def main():

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    if CONFIG["UseProxys"]:
        logger.info("Using proxys.")
        proxys = load_proxys()
        if proxys is None:
            logger.err("No proxys are loaded.")
            return
        else:
            logger.info(f"Loaded {len(proxys)} proxys.")

        for proxy in proxys:
            PROXY_QUEUE.put(proxy)
    else:
        logger.info("Not using proxys.")

    tokens = load_tokens()
    if len(tokens) == 0:
        logger.err("No tokens are loaded.")
        return
    else:
        logger.info(f"Loaded {len(tokens)} tokens.")

    for token in tokens:
        TOKEN_QUEUE.put(token)
    threads = []
    while not TOKEN_QUEUE.empty():
        token = TOKEN_QUEUE.get()
        t = threading.Thread(target=threaded_server_spam, args=(token,))
        t.start()
        threads.append(t)
        logger.suc(f"Started thread for token [...{token[-5:]}]")

    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
