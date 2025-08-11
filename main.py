#!/usr/bin/env python3
import os
import time
import logging
import sqlite3
import requests
from bs4 import BeautifulSoup
import feedparser
from telegram import Bot, TelegramError

# --- Конфигурация через переменные окружения ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")          # Твой токен
CHANNEL = os.environ.get("CHANNEL", "@kazucheba")
LOG_CHAT_ID = os.environ.get("LOG_CHAT_ID")     # твой numeric id, например 6620422054
INTERVAL = int(os.environ.get("INTERVAL", 1800))  # 30 мин по умолчанию
DB_PATH = os.environ.get("DB_PATH", "seen.db")

KEYWORDS = [kw.lower() for kw in [
    "школа","вуз","высшее","образование","ент","экзамен",
    "институт","университет","ученик","школьник","учитель","педагог","класс"
]]

RSS_SOURCES = [
    "https://tengrinews.kz/rss/all.rss",
    "https://www.nur.kz/rss/all.rss",
    # добавь по желанию ещё RSS
]
HTML_SOURCES = [
    "https://tengrinews.kz",
    "https://www.nur.kz",
    "https://www.zakon.kz",
    "https://informburo.kz",
    "https://baq.kz",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("kazedu")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN не задан. Установите переменную окружения BOT_TOKEN.")
    raise SystemExit(1)

bot = Bot(token=BOT_TOKEN)

def init_db(path=DB_PATH):
    conn = sqlite3.connect(path, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS seen (url TEXT PRIMARY KEY, ts INTEGER)")
    conn.commit()
    return conn

db = init_db()

def already_seen(url):
    cur = db.cursor()
    cur.execute("SELECT 1 FROM seen WHERE url = ?", (url,))
    return cur.fetchone() is not None

def mark_seen(url):
    cur = db.cursor()
    cur.execute("INSERT OR IGNORE INTO seen(url, ts) VALUES(?, ?)", (url, int(time.time())))
    db.commit()

def send_log(text):
    if not LOG_CHAT_ID:
        logger.info("LOG_CHAT_ID не задан.")
        return
    try:
        bot.send_message(chat_id=LOG_CHAT_ID, text=f"📝 {text}")
    except Exception as e:
        logger.exception("Ошибка отправки лога: %s", e)

def fetch_rss_links(rss_url):
    try:
        feed = feedparser.parse(rss_url)
        items = []
        for entry in feed.entries:
            link = entry.get("link") or entry.get("id")
            title = entry.get("title", "").strip()
            items.append((title, link))
        return items
    except Exception as e:
        logger.exception("RSS parse error %s", rss_url)
        send_log(f"[Ошибка RSS] {rss_url} — {e}")
        return []

def fetch_html_links(base_url):
    results = []
    try:
        r = requests.get(base_url, timeout=12, headers={"User-Agent":"Mozilla/5.0"})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('/'):
                href = base_url.rstrip('/') + href
            if href.startswith('http'):
                title = a.get_text(strip=True) or a.get('title') or href
                results.append((title, href))
    except Exception as e:
        logger.exception("HTML fetch error %s", base_url)
        send_log(f"[Ошибка парсинга HTML] {base_url} — {e}")
    return results

def contains_keyword(text):
    if not text:
        return False
    low = text.lower()
    for kw in KEYWORDS:
        if kw in low:
            return True
    return False

def publish(title, url):
    try:
        text = f"📢 <b>{title}</b>\n{url}"
        bot.send_message(chat_id=CHANNEL, text=text, parse_mode="HTML")
        send_log(f"Опубликовано: {title} — {url}")
        mark_seen(url)
        return True
    except TelegramError as e:
        logger.exception("Telegram API error")
        send_log(f"[Ошибка Telegram] {e}")
        return False
    except Exception as e:
        logger.exception("Unexpected publish error")
        send_log(f"[Ошибка публикации] {e}")
        return False

def run_cycle():
    found = []
    for rss in RSS_SOURCES:
        items = fetch_rss_links(rss)
        for title, link in items:
            if link and not already_seen(link) and (contains_keyword(title) or contains_keyword(link)):
                found.append((title or "Без заголовка", link))
    for url in HTML_SOURCES:
        items = fetch_html_links(url)
        for title, link in items:
            if link and not already_seen(link) and (contains_keyword(title) or contains_keyword(link)):
                found.append((title or "Без заголовка", link))

    unique = {}
    for t, l in found:
        if l not in unique:
            unique[l] = t

    count = 0
    for link, title in unique.items():
        if count >= 5:
            break
        if publish(title, link):
            count += 1

    if count == 0:
        send_log("Новых релевантных новостей не найдено в этом цикле.")

def main_loop():
    send_log("Бот запущен.")
    while True:
        try:
            run_cycle()
        except Exception as e:
            logger.exception("Ошибка в run_cycle: %s", e)
            send_log(f"[Критическая ошибка] {e}")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main_loop()
