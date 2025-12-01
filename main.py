import os
import logging
import asyncio
import time
import schedule
import html
from dotenv import load_dotenv
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

import scraper
import db_manager

# Load environment variables
load_dotenv()

# Configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
CHECK_INTERVAL_MINUTES = 15

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def send_to_telegram(bot, news_item):
    """Sends a formatted news message to Telegram."""
    title = news_item['title']
    url = news_item['url']
    summary = news_item.get('summary', '')

    # Escape HTML special characters to avoid parsing errors
    safe_title = html.escape(title)
    safe_summary = html.escape(summary)

    # HTML formatting
    message = f"<b>{safe_title}</b>\n\n{safe_summary}\n\n<a href='{url}'>Читать далее</a>"

    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode=ParseMode.HTML)
        logger.info(f"Sent: {title}")
        db_manager.mark_as_published(url)
    except TelegramError as e:
        logger.error(f"Failed to send message: {e}")

async def process_news(bot):
    """Fetches, filters, and sends news."""
    logger.info("Starting news check cycle...")

    all_news = []

    # 1. Fetch RSS News
    try:
        rss_news = scraper.fetch_rss_news()
        all_news.extend(rss_news)
    except Exception as e:
        logger.error(f"Error fetching RSS news: {e}")

    # 2. Fetch Web News
    # Note: Using a test URL or the one from original code.
    # Tengrinews was used in original code, so keeping it as default in scraper.py
    try:
        web_news = scraper.fetch_web_news()
        all_news.extend(web_news)
    except Exception as e:
        logger.error(f"Error scraping web news: {e}")

    # 3. Filter and Send
    for news_item in all_news:
        url = news_item.get('url')
        if not url:
            continue

        if not db_manager.is_published(url):
            await send_to_telegram(bot, news_item)
            # Sleep briefly to avoid hitting rate limits
            await asyncio.sleep(1)
        else:
            logger.debug(f"Skipping already published: {url}")

def job():
    """Wrapper for the scheduled job to run async code."""
    # Since schedule is synchronous, we need to run the async function
    # We create a new event loop for this run or use an existing one if appropriate.
    asyncio.run(run_job_async())

async def run_job_async():
    bot = Bot(token=TOKEN)
    await process_news(bot)

def main():
    if not TOKEN or not CHANNEL_ID:
        logger.error("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID not set in .env")
        logger.error("Please create a .env file with these variables.")
        return

    # Initialize Database
    db_manager.init_db()

    # Schedule the job
    logger.info(f"Scheduling news check every {CHECK_INTERVAL_MINUTES} minutes.")
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(job)

    # Run immediately once on startup
    try:
        job()
    except Exception as e:
        logger.error(f"Error during initial job run: {e}")

    # Main loop
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    main()
