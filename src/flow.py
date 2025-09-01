from Queues import TOKEN_QUEUE
from Logger import logger
from initialization_functions import grab_proxy
from discord_functions import pull_serverids, pull_channels, send_message_flow
import queue, threading


def ServerSpamFlow(token):
    CHANNEL_QUEUE = []
    CHANNEL_QUEUE2 = []
    proxy = grab_proxy()

    serverIds = pull_serverids(token, proxy)
    if not serverIds:
        exit("Failed to pull server ids. Exiting thread.")

    for serverId in serverIds:
        result = pull_channels(token, serverId, proxy, CHANNEL_QUEUE)
        if not result:
            exit("Failed to pull channels. Exiting thread.")

        thread = threading.Thread(
            target=send_message_flow,
            args=(token, proxy, CHANNEL_QUEUE, CHANNEL_QUEUE2)
        )
        thread.start()


def threaded_server_spam(token):
    try:
        ServerSpamFlow(token)  # make sure ServerSpamFlow accepts token & proxy as parameters
    except Exception as e:
        logger.err(f"Error in thread for token [...{token[-5:]}]: {e}")
