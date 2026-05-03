# database.py

import sqlite3
from datetime import datetime

DB_NAME = "prices.db"

def init_db():
    """Creates the database tables if they don't already exist."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                threshold REAL NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                price REAL NOT NULL,
                checked_at TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Set default currency if not already set
        cursor.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('currency', 'GBP')
        """)

        conn.commit()


def get_setting(key):
    """Returns a setting value by key."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None


def set_setting(key, value):
    """Saves or updates a setting."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, value))
        conn.commit()


def add_product(name, url, threshold):
    """Adds a new product to track. Returns True if successful, False if URL already exists."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO products (name, url, threshold, created_at)
                VALUES (?, ?, ?, ?)
            """, (name, url, threshold, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False


def remove_product(product_id):
    """Removes a product and all its price history."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM price_history WHERE product_id = ?", (product_id,))
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()


def get_all_products():
    """Returns all tracked products."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products ORDER BY created_at DESC")
        return cursor.fetchall()


def get_product(product_id):
    """Returns a single product by ID."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        return cursor.fetchone()


def save_price(product_id, price):
    """Saves a price check result to history."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO price_history (product_id, price, checked_at)
            VALUES (?, ?, ?)
        """, (product_id, price, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()


def get_price_history(product_id):
    """Returns all price history for a product, oldest first."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM price_history
            WHERE product_id = ?
            ORDER BY checked_at ASC
        """, (product_id,))
        return cursor.fetchall()


def get_latest_price(product_id):
    """Returns the most recent price check for a product."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM price_history
            WHERE product_id = ?
            ORDER BY checked_at DESC
            LIMIT 1
        """, (product_id,))
        return cursor.fetchone()