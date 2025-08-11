import os
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv("BOT_TOKEN")  # Токен из GitHub Secrets
CHANNEL_ID = os.getenv("CHANNEL_ID")  # ID или @username канала из Secrets

NEWS_URL = "https://tengrinews.kz"

# Парсинг новостей
def get_news():
    response = requests.get(NEWS_URL)
    soup = BeautifulSoup(response.text, "html.parser")
    headlines = soup.select(".content_main_item_title a")[:5]  # первые 5 новостей
    news_list = []
    for h in headlines:
        title = h.get_text(strip=True)
        link = NEWS_URL + h["href"]
        news_list.append(f"{title}\n{link}")
    return "\n\n".join(news_list)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот, который будет присылать новости в канал.")

# Команда /news
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    news_data = get_news()
    await update.message.reply_text(news_data)

# Автопостинг в канал
async def post_news_to_channel(app):
    news_data = get_news()
    await app.bot.send_message(chat_id=CHANNEL_ID, text=news_data)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("news", news))

    # Пример: при запуске сразу отправляем новости в канал
    app.job_queue.run_once(lambda ctx: post_news_to_channel(app), 5)

    app.run_polling()
