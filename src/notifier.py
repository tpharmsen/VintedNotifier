import http.client
import logging
import urllib.parse

def notify(API_TOKEN: str, USER_KEY: str, item_name: str, item_url: str, item_price: str, item_brand: str, item_size: str):

    message = f"""
        🚨 {item_name} 🚨 
        Price: {item_price['amount']} {item_price['currency_code']}
        Brand: {item_brand}
        Size: {item_size}
        URL: {item_url}
    """
    data = urllib.parse.urlencode({
        "token": API_TOKEN,
        "user": USER_KEY,
        "message": message,
    }).encode("utf-8")

    conn = http.client.HTTPSConnection("api.pushover.net:443")
    conn.request(
        "POST",
        "/1/messages.json",
        body=data,
        headers={"Content-type": "application/x-www-form-urlencoded"}
    )

    response = conn.getresponse()
    response_text = response.read().decode()
    if response.status == 200:
        logging.info("Notification sent successfully!")
    else:
        logging.info("Error sending notification:" + str(response.status))

