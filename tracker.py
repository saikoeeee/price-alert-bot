# tracker.py

import requests
import smtplib
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os
import config
import database


CURRENCY_SYMBOLS = {
    "GBP": "£",
    "USD": "$",
    "EUR": "€",
    "SGD": "S$",
    "AUD": "A$",
    "JPY": "¥",
    "CAD": "C$"
}


def get_exchange_rate(to_currency):
    """
    Fetches the current exchange rate from GBP to the target currency.
    Returns 1.0 as fallback if the request fails.
    """
    if to_currency == "GBP":
        return 1.0
    try:
        response = requests.get(
            f"https://api.frankfurter.app/latest?from=GBP&to={to_currency}",
            timeout=10
        )
        data = response.json()
        return data["rates"][to_currency]
    except Exception as e:
        print(f"Could not fetch exchange rate for {to_currency}: {e}")
        return 1.0


def convert_price(price_gbp, rate):
    """Converts a GBP price using the given exchange rate."""
    return round(price_gbp * rate, 2)


def get_price(url):
    """
    Fetches the current price from a given URL.
    Returns the price as a float in GBP, or None if it fails.
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
            print(f"Could not find price element on: {url}")
            return None

    except requests.RequestException as e:
        print(f"Network error for {url}: {e}")
        return None
    except ValueError as e:
        print(f"Could not parse price from {url}: {e}")
        return None


def send_alert(product_name, product_url, current_price, threshold, currency_symbol):
    """Sends an email alert for a product that dropped below its threshold."""
    subject = f"Price Alert: {product_name} dropped to {currency_symbol}{current_price:.2f}"
    body = (
        f"Good news! {product_name} has dropped to {currency_symbol}{current_price:.2f}, "
        f"which is below your threshold of {currency_symbol}{threshold:.2f}.\n\n"
        f"Check it out here: {product_url}"
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
            server.sendmail(
                config.EMAIL_SENDER,
                config.EMAIL_RECEIVER,
                message.as_string()
            )
        print(f"Alert sent for {product_name}.")
    except smtplib.SMTPException as e:
        print(f"Failed to send alert for {product_name}: {e}")


def generate_chart(product_id, product_name, currency_code, currency_symbol, rate):
    """
    Generates a price history chart for a product and saves it
    to the static/charts folder. Prices are converted from GBP.
    """
    history = database.get_price_history(product_id)

    if len(history) < 2:
        return

    dates = [
        datetime.strptime(row["checked_at"], "%Y-%m-%d %H:%M:%S")
        for row in history
    ]
    prices = [convert_price(row["price"], rate) for row in history]

    fig, ax = plt.subplots(figsize=(10, 4))

    ax.plot(dates, prices, color="#4f8ef7", linewidth=2, marker="o", markersize=4)
    ax.fill_between(dates, prices, alpha=0.1, color="#4f8ef7")

    ax.set_title(f"Price History: {product_name} ({currency_code})", fontsize=14, pad=15)
    ax.set_xlabel("Date", fontsize=11)
    ax.set_ylabel(f"Price ({currency_symbol})", fontsize=11)

    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"{currency_symbol}{x:.2f}")
    )

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    fig.autofmt_xdate()

    ax.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()

    charts_dir = os.path.join("static", "charts")
    os.makedirs(charts_dir, exist_ok=True)

    chart_path = os.path.join(charts_dir, f"product_{product_id}.png")
    fig.savefig(chart_path, dpi=100, bbox_inches="tight")
    plt.close(fig)


def check_all_products():
    """
    Checks the price of every tracked product, saves to the database,
    generates a chart and sends alerts where needed.
    """
    products = database.get_all_products()

    if not products:
        print("No products to check.")
        return

    currency_code = database.get_setting("currency") or "GBP"
    currency_symbol = CURRENCY_SYMBOLS.get(currency_code, currency_code)
    rate = get_exchange_rate(currency_code)

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking {len(products)} product(s)... (Currency: {currency_code})")

    for product in products:
        print(f"  Checking: {product['name']}")
        price_gbp = get_price(product["url"])

        if price_gbp is not None:
            database.save_price(product["id"], price_gbp)
            generate_chart(
                product["id"],
                product["name"],
                currency_code,
                currency_symbol,
                rate
            )

            converted_price = convert_price(price_gbp, rate)
            converted_threshold = convert_price(product["threshold"], rate)

            print(f"  Price: {currency_symbol}{converted_price:.2f} (threshold: {currency_symbol}{converted_threshold:.2f})")

            if price_gbp < product["threshold"]:
                print(f"  Below threshold. Sending alert...")
                send_alert(
                    product["name"],
                    product["url"],
                    converted_price,
                    converted_threshold,
                    currency_symbol
                )
        else:
            print(f"  Could not retrieve price.")

    print("Check complete.\n")