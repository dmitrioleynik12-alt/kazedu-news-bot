import sqlite3
import logging
from datetime import datetime

DB_NAME = "published_news.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    """Initializes the database and creates the table if it doesn't exist."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS published_news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                published_at TIMESTAMP
            )
        """)
        conn.commit()
    logging.info("Database initialized.")

def is_published(url):
    """Checks if the URL has already been published."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM published_news WHERE url = ?", (url,))
        result = cursor.fetchone()
        return result is not None
    finally:
        # Don't close the connection if it's the shared memory connection
        # But standard behavior is to close.
        # For testing with :memory: and mocked get_connection, closing it destroys the DB or makes it unusable.
        # However, in production, we want to close it.
        # The issue is that in production get_connection returns a NEW connection every time.
        # In test, it returns the SAME connection.
        # If we close it here, the test fails.
        # So we should only close if we created it locally or rely on GC (not good).
        # Better: let context manager handle it if possible, but sqlite3 connection is a context manager for transaction, not closing.
        # Let's just check if it's the mocked one? No.

        # In standard usage:
        # conn = sqlite3.connect(...) -> new object
        # conn.close() -> closes it.

        # In test usage:
        # conn = self.conn (persistent)
        # conn.close() -> closes the shared connection.

        # So we should NOT close the connection inside these functions if we want to support the shared connection injection pattern properly, OR we should assume get_connection returns a disposable connection.
        # Since I changed db_manager to use get_connection(), I can just NOT close it in the test by mocking close?
        pass
        conn.close()

def mark_as_published(url):
    """Marks the URL as published."""
    try:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO published_news (url, published_at) VALUES (?, ?)",
                (url, datetime.now())
            )
            conn.commit()
        finally:
            conn.close()
        logging.info(f"Marked as published: {url}")
    except sqlite3.IntegrityError:
        logging.warning(f"URL already exists in database: {url}")
