# tracker.py

import requests
import smtplib
import time
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config

def get_price(url):
    """
    Fetches the current price of a product from the given URL.
    Returns the price as a float, or None if it fails.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        price_tag = soup.find("p", class_="price_color")

        if price_tag:
            price_text = price_tag.text.strip().replace("£", "").replace("Â", "")
            return float(price_text)
        else:
            print("Could not find price element on page.")
            return None

    except requests.RequestException as e:
        print(f"Network error: {e}")
        return None
    except ValueError as e:
        print(f"Could not parse price: {e}")
        return None


def send_alert(current_price):
    """
    Sends an email alert with the current price.
    """
    subject = f"Price Alert: Price dropped to £{current_price:.2f}"
    body = (
        f"Good news! The price has dropped to £{current_price:.2f}, "
        f"which is below your threshold of £{config.PRICE_THRESHOLD:.2f}.\n\n"
        f"Check it out here: {config.URL}"
    )

    message = MIMEMultipart()
    message["From"] = config.EMAIL_SENDER
    message["To"] = config.EMAIL_RECEIVER
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
            server.sendmail(config.EMAIL_SENDER, config.EMAIL_RECEIVER, message.as_string())
        print("Alert email sent successfully.")
    except smtplib.SMTPException as e:
        print(f"Failed to send email: {e}")


def run_tracker(check_interval_minutes=60):
    """
    Main loop. Checks the price at a set interval and sends
    an alert if the price falls below the configured threshold.
    """
    print(f"Tracker started. Checking every {check_interval_minutes} minute(s).")
    print(f"Alert threshold: £{config.PRICE_THRESHOLD:.2f}\n")

    while True:
        print("Checking price...")
        current_price = get_price(config.URL)

        if current_price is not None:
            print(f"Current price: £{current_price:.2f}")

            if current_price < config.PRICE_THRESHOLD:
                print("Price is below threshold. Sending alert...")
                send_alert(current_price)
            else:
                print("Price is above threshold. No alert sent.")

        print(f"Next check in {check_interval_minutes} minute(s).\n")
        time.sleep(check_interval_minutes * 60)


if __name__ == "__main__":
    run_tracker(check_interval_minutes=60)