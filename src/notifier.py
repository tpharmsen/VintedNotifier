import http.client
import logging
import urllib.parse
from config import NOTIFY_TYPE

def notify(logger, message: str, TOKEN: str, TARGET_ID: str):
    try:
        if NOTIFY_TYPE.lower() == "pushover":
            data = urllib.parse.urlencode({
                "token": TOKEN,      # Pushover API token
                "user": TARGET_ID,   # Pushover user key
                "message": message,
            }).encode("utf-8")

            conn = http.client.HTTPSConnection("api.pushover.net", 443)
            conn.request(
                "POST",
                "/1/messages.json",
                body=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

        elif NOTIFY_TYPE.lower() == "telegram":
            data = urllib.parse.urlencode({
                "chat_id": TARGET_ID,  # Telegram chat ID
                "text": message
            })

            conn = http.client.HTTPSConnection("api.telegram.org")
            conn.request(
                "POST",
                f"/bot{TOKEN}/sendMessage",  # Telegram bot token
                body=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

        else:
            raise ValueError("Unknown notification handler type")

        response = conn.getresponse()
        response_text = response.read().decode()

        if response.status == 200:
            logger.info("%s notification sent successfully!", type.capitalize())
        else:
            logger.error(
                "%s notification failed (%s): %s",
                NOTIFY_TYPE.capitalize(),
                response.status,
                response_text
            )

        conn.close()

    except Exception as e:
        logger.error("Notification error (%s): %s", type, e)
