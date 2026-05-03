# app.py

from flask import Flask, render_template, request, redirect, url_for, flash
from apscheduler.schedulers.background import BackgroundScheduler
import database
import tracker
import config

app = Flask(__name__)
app.secret_key = "pricealertbot"

CURRENCY_SYMBOLS = {
    "GBP": "£",
    "USD": "$",
    "EUR": "€",
    "SGD": "S$",
    "AUD": "A$",
    "JPY": "¥",
    "CAD": "C$"
}


def get_currency_context():
    """Returns current currency code, symbol and exchange rate."""
    currency_code = database.get_setting("currency") or "GBP"
    currency_symbol = CURRENCY_SYMBOLS.get(currency_code, currency_code)
    rate = tracker.get_exchange_rate(currency_code)
    return currency_code, currency_symbol, rate


def start_scheduler():
    """Starts the background scheduler that checks prices automatically."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=tracker.check_all_products,
        trigger="interval",
        minutes=config.CHECK_INTERVAL_MINUTES
    )
    scheduler.start()
    print(f"Scheduler started. Checking every {config.CHECK_INTERVAL_MINUTES} minute(s).")


@app.route("/")
def index():
    """Main dashboard showing all tracked products."""
    products = database.get_all_products()
    currency_code, currency_symbol, rate = get_currency_context()

    product_data = []
    for product in products:
        latest = database.get_latest_price(product["id"])
        price_gbp = latest["price"] if latest else None
        converted_price = tracker.convert_price(price_gbp, rate) if price_gbp else None
        converted_threshold = tracker.convert_price(product["threshold"], rate)

        product_data.append({
            "id": product["id"],
            "name": product["name"],
            "url": product["url"],
            "threshold": converted_threshold,
            "latest_price": converted_price,
            "checked_at": latest["checked_at"] if latest else None,
            "below_threshold": (price_gbp < product["threshold"] if price_gbp else False)
        })

    return render_template(
        "index.html",
        products=product_data,
        currency_code=currency_code,
        currency_symbol=currency_symbol,
        supported_currencies=CURRENCY_SYMBOLS
    )


@app.route("/add", methods=["POST"])
def add_product():
    """Handles adding a new product from the dashboard form."""
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    threshold = request.form.get("threshold", "").strip()

    if not name or not url or not threshold:
        flash("All fields are required.", "error")
        return redirect(url_for("index"))

    try:
        threshold = float(threshold)
    except ValueError:
        flash("Threshold must be a number.", "error")
        return redirect(url_for("index"))

    # Threshold is entered in the user's currency, convert back to GBP for storage
    _, _, rate = get_currency_context()
    threshold_gbp = round(threshold / rate, 2)

    success = database.add_product(name, url, threshold_gbp)

    if success:
        flash(f'"{name}" added successfully.', "success")
        tracker.check_all_products()
    else:
        flash("That URL is already being tracked.", "error")

    return redirect(url_for("index"))


@app.route("/remove/<int:product_id>", methods=["POST"])
def remove_product(product_id):
    """Handles removing a product."""
    product = database.get_product(product_id)
    if product:
        database.remove_product(product_id)
        flash(f'"{product["name"]}" removed.', "success")
    return redirect(url_for("index"))


@app.route("/set_currency", methods=["POST"])
def set_currency():
    """Saves the user's preferred currency and regenerates all charts."""
    currency = request.form.get("currency", "GBP")
    if currency in CURRENCY_SYMBOLS:
        database.set_setting("currency", currency)
        flash(f"Currency updated to {currency}.", "success")
        # Regenerate all charts in the new currency
        tracker.check_all_products()
    else:
        flash("Invalid currency selected.", "error")
    return redirect(url_for("index"))


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    """Shows price history and chart for a single product."""
    product = database.get_product(product_id)

    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("index"))

    currency_code, currency_symbol, rate = get_currency_context()
    history = database.get_price_history(product_id)
    latest = database.get_latest_price(product_id)

    converted_latest_price = (
        tracker.convert_price(latest["price"], rate) if latest else None
    )
    converted_threshold = tracker.convert_price(product["threshold"], rate)

    return render_template(
        "product.html",
        product=product,
        history=history,
        latest=latest,
        converted_latest_price=converted_latest_price,
        converted_threshold=converted_threshold,
        currency_code=currency_code,
        currency_symbol=currency_symbol,
        rate=rate
    )


if __name__ == "__main__":
    database.init_db()
    start_scheduler()
    app.run(debug=True)