from Config import CONFIG
from Logger import logger
from initialization_functions import parse_time_range, check_token
import os, random, requests, time


def pull_serverids(token, proxy, max_retries=CONFIG["MaxRetriesForFailedRequests"], delay=CONFIG["DelayBetweenFailedRequests"]):
    logger.info(f"Pulling server ids [...{token[-5:]}]")
    proxies = {
        "http": f"http://{proxy}",
        "https": f"https://{proxy}",
    }

    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }

    url = "https://discord.com/api/v9/users/@me/guilds"
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=headers, proxies=proxies)
            if response.status_code == 200:
                data = response.json()
                guild_ids = [g["id"] for g in data]
                logger.info(f"[...{token[-5:]}] Pulled servers: "+ str([{"id": g["id"], "name": g["name"]} for g in data]))
                return guild_ids
            else:
                logger.err(f"Failed to pull server ids for token [...{token[-5:]}]")
        except requests.exceptions.RequestException as e:
            logger.err(f"Attempt {attempt}: Error in pull server ids. {e}")
            if attempt < max_retries:
                time.sleep(delay)  # wait before retrying
            else:
                return None

def can_send_in_channel(user_id, user_roles, channel):
    SEND_MESSAGES = 0x800
    can_send = False  # default

    # Step 1: everyone overwrite (id = guild_id)
    for overwrite in channel.get("permission_overwrites", []):
        if overwrite["id"] == channel["guild_id"]:  # @everyone
            allow = int(overwrite["allow"])
            deny = int(overwrite["deny"])
            if deny & SEND_MESSAGES:
                can_send = False
            if allow & SEND_MESSAGES:
                can_send = True

    # Step 2: role overwrites
    for overwrite in channel.get("permission_overwrites", []):
        if overwrite["type"] == 0 and overwrite["id"] in user_roles:
            allow = int(overwrite["allow"])
            deny = int(overwrite["deny"])
            if deny & SEND_MESSAGES:
                can_send = False
            if allow & SEND_MESSAGES:
                can_send = True

    # Step 3: member overwrite (highest priority)
    for overwrite in channel.get("permission_overwrites", []):
        if overwrite["type"] == 1 and overwrite["id"] == user_id:
            allow = int(overwrite["allow"])
            deny = int(overwrite["deny"])
            if deny & SEND_MESSAGES:
                can_send = False
            if allow & SEND_MESSAGES:
                can_send = True

    return can_send

def pull_channels(token, guild_id, proxy, CHANNEL_QUEUE, max_retries=CONFIG["MaxRetriesForFailedRequests"], delay=CONFIG["DelayBetweenFailedRequests"]):
    logger.info(f"[...{token[-5:]}] Pulling channelIds")
    USER_ID = pull_userId(token, proxy)
    if not USER_ID:
        return None

    user_roles = pull_user_roles(token, guild_id, USER_ID, proxy)

    proxies = {"http": f"http://{proxy}", "https": f"https://{proxy}"}
    headers = {"Authorization": token, "Content-Type": "application/json"}
    url = f"https://discord.com/api/v9/guilds/{guild_id}/channels"

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, proxies=proxies)
            resp.raise_for_status()
            channels = resp.json()

            for ch in channels:
                if ch["type"] == 0:  # text channel
                    if can_send_in_channel(USER_ID, user_roles, ch):
                        CHANNEL_QUEUE.append(ch["id"])
                        logger.info(f"[...{token[-5:]}] Sendable channel: " +
                                    str({"id": ch["id"], "name": ch['name'].encode('ascii', errors='ignore').decode()}))
                        return True
            return False
        except Exception as e:
            logger.err(f"[...{token[-5:]}] Attempt {attempt}: Error in fetching channels [...{token[-5:]}] {e}")
            if attempt < max_retries:
                time.sleep(delay)
            else:
                return None


def pull_userId(token, proxy, max_retries=CONFIG["MaxRetriesForFailedRequests"], delay=CONFIG["DelayBetweenFailedRequests"]):
    result = check_token(token)
    if not result:
        return None  # changed False -> None for consistency
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    proxies = {
        "http": f"http://{proxy}",
        "https": f"https://{proxy}",
    }
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get("https://discord.com/api/v10/users/@me", headers=headers, proxies=proxies)
            if response.status_code != 200:
                logger.err(f"[...{token[-5:]}] Attempt {attempt}: Failed to fetch user id (status {response.status_code}): {response.text}")
                if attempt < max_retries:
                    time.sleep(delay)
                    continue
                else:
                    return None
            user_data = response.json()
            if "id" not in user_data:
                logger.err(f"[...{token[-5:]}] Attempt {attempt}: 'id' not found in response: {user_data}")
                return None
            return user_data["id"]
        except requests.exceptions.RequestException as e:
            logger.err(f"[...{token[-5:]}] Attempt {attempt}: Error in getting user id. {e}")
            if attempt < max_retries:
                time.sleep(delay)
            else:
                return None

def pull_user_roles(token, guild_id, user_id, proxy, max_retries=CONFIG["MaxRetriesForFailedRequests"], delay=CONFIG["DelayBetweenFailedRequests"]):
    headers = {"Authorization": token, "Content-Type": "application/json"}
    proxies = {"http": f"http://{proxy}", "https": f"https://{proxy}"}
    url = f"https://discord.com/api/v9/guilds/{guild_id}/members/{user_id}"
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, proxies=proxies)
            resp.raise_for_status()
            data = resp.json()
            return data.get("roles", [])
        except requests.exceptions.RequestException as e:
            logger.err(f"[...{token[-5:]}] Attempt {attempt}: Error in getting user roles. {e}")
            if attempt < max_retries:
                time.sleep(delay)
            else:
                return []


def grab_channel(CHANNEL_QUEUE, CHANNEL_QUEUE2, token):
    if not CHANNEL_QUEUE:  # empty list
        logger.info(f"[...{token[-5:]}] Recycling channels.. Waiting TimeBetweenServerSpam")
        time.sleep(parse_time_range(CONFIG["TimeBetweenServerSpam"]))
        CHANNEL_QUEUE.extend(CHANNEL_QUEUE2)  # recycle all channels

    channel = CHANNEL_QUEUE.pop(0)  # remove first item
    CHANNEL_QUEUE2.append(channel)
    return channel


def send_message(channel_id, token, proxy, message,  max_retries=CONFIG["MaxRetriesForFailedRequests"], delay=CONFIG["DelayBetweenFailedRequests"]):
    result = check_token(token)
    if not result:
        return False
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    data = {"content": message}

    proxies = None
    if proxy:
        proxies = {
            "http": f"http://{proxy}",
            "https": f"https://{proxy}",
        }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=data, proxies=proxies)
            if resp.status_code == 200 or resp.status_code == 201:
                logger.info(f"[...{token[-5:]}] Sent message to channel {channel_id}")
                return True
            else:
                logger.err(f"[...{token[-5:]}] Failed to send message (status {resp.status_code}): {resp.text}")
        except requests.exceptions.RequestException as e:
            logger.err(f"[...{token[-5:]}] Attempt {attempt}: Error sending message. {e}")

        if attempt < max_retries:
            time.sleep(delay)

    return False

message_path = os.path.join(os.path.dirname(__file__), "..", "input", "messages.txt")
message_path = os.path.abspath(message_path)

with open(message_path, "r") as f:
    MESSAGES = f.read()

def return_Message():
    return random.choice(MESSAGES)

def send_message_flow(token, proxy, CHANNEL_QUEUE, CHANNEL_QUEUE2):
        while True:
            channelid = grab_channel(CHANNEL_QUEUE, CHANNEL_QUEUE2, token)
            result = send_message(channelid, token, proxy,return_Message())
            if not result:
                if channelid in CHANNEL_QUEUE2:
                    CHANNEL_QUEUE2.remove(channelid)
            time.sleep(parse_time_range(CONFIG["TimeBetweenChannelServerSpam"]))

def get_dm_channels(token, proxy=None, max_retries=CONFIG["MaxRetriesForFailedRequests"], delay=CONFIG["DelayBetweenFailedRequests"]):
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    proxies = None
    if proxy:
        proxies = {"http": f"http://{proxy}", "https": f"https://{proxy}"}

    url = "https://discord.com/api/v9/users/@me/channels"
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, proxies=proxies)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            logger.err(f"Attempt {attempt}: Error fetching DM channels [...{token[-5:]}] {e}")
            if attempt < max_retries:
                time.sleep(delay)
            else:
                return []

def send_dm(token, channel_id, message, proxy=None, max_retries=CONFIG["MaxRetriesForFailedRequests"], delay=CONFIG["DelayBetweenFailedRequests"]):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    data = {"content": message}
    proxies = None
    if proxy:
        proxies = {"http": f"http://{proxy}", "https": f"https://{proxy}"}

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=data, proxies=proxies)
            if resp.status_code in (200, 201):
                return True
            else:
                logger.err(f"Attempt {attempt}: Failed to send DM (status {resp.status_code}) [...{token[-5:]}]: {resp.text}")
        except requests.exceptions.RequestException as e:
            logger.err(f"Attempt {attempt}: Error sending DM [...{token[-5:]}] {e}")

        if attempt < max_retries:
            time.sleep(delay)

    return False
