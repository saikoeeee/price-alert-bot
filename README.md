# Price Alert Bot

A Python automation script that monitors a product's price
and sends an email alert when it drops below a set threshold.

## Features
- Automated price scraping with BeautifulSoup
- Email notifications via Gmail SMTP
- Configurable check interval and price threshold
- Error handling for network failures and parsing issues

## Tech Stack
- Python 3
- requests
- BeautifulSoup4
- smtplib (standard library)

## Setup

1. Clone the repository
2. Install dependencies: python -m pip install -r requirements.txt
3. Copy config.example.py to config.py and fill in your details
4. Run: python tracker.py

## How It Works
The script fetches the product page at a set interval, parses
the price from the HTML, and compares it to your threshold.
If the price has dropped, it sends an email alert using Gmail's
SMTP server.

## Notes
- Tested on books.toscrape.com (a safe, legal scraping practice site)
- Adapt the CSS selector in get_price() for other websites