import feedparser
import requests
from bs4 import BeautifulSoup
import logging

# Set up logging
logger = logging.getLogger(__name__)

def fetch_rss_news(feed_url="https://news.google.com/rss"):
    """
    Parses news from an RSS feed.

    Args:
        feed_url (str): The URL of the RSS feed.

    Returns:
        list: A list of dictionaries containing title, url, and summary.
    """
    logger.info(f"Fetching RSS feed from: {feed_url}")
    feed = feedparser.parse(feed_url)
    news_list = []

    for entry in feed.entries[:10]: # Limit to 10 entries
        title = entry.title
        url = entry.link
        summary = entry.summary if 'summary' in entry else ""
        # Sometimes Google News RSS summary is HTML, we might want to strip tags or keep it basic.
        # For now, we take it as is or a basic cleanup could be done.

        news_list.append({
            "title": title,
            "url": url,
            "summary": summary
        })

    return news_list

def fetch_web_news(target_url="https://tengrinews.kz"):
    """
    Scrapes news from a web page.

    Args:
        target_url (str): The URL of the news site.

    Returns:
        list: A list of dictionaries containing title, url, and summary.
    """
    logger.info(f"Scraping web page: {target_url}")
    try:
        response = requests.get(target_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        news_list = []

        # Logic specific to Tengrinews as in the original main.py, but enhanced
        headlines = soup.select(".content_main_item_title a")[:5]

        for h in headlines:
            title = h.get_text(strip=True)
            # Handle relative URLs
            if h["href"].startswith("http"):
                url = h["href"]
            else:
                # Ensure we don't double the slash if one exists
                base = target_url.rstrip('/')
                path = h["href"].lstrip('/')
                url = f"{base}/{path}"

            # Try to fetch summary - usually involves visiting the link or finding adjacent text
            # For this task: "extract title, URL and first paragraph"
            # Getting the first paragraph requires visiting the link.
            summary = get_article_summary(url)

            news_list.append({
                "title": title,
                "url": url,
                "summary": summary
            })

        return news_list
    except Exception as e:
        logger.error(f"Error scraping web news: {e}")
        return []

def get_article_summary(article_url):
    """
    Helper to fetch the first paragraph of an article.
    """
    try:
        response = requests.get(article_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # This selector is generic and might need adjustment based on the target site
        # For tengrinews, the content is usually in .content_main_text or similar.
        # Let's try to find the first <p> in the main content area.
        # We'll look for common content containers.
        content = soup.select_one(".content_main_text") or soup.select_one("article") or soup.select_one("main") or soup.body

        if content:
            paragraphs = content.find_all("p")
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 20: # Filter out short empty paragraphs
                    return text
        return "No summary available."
    except Exception as e:
        logger.warning(f"Could not fetch summary for {article_url}: {e}")
        return "Summary unavailable."
