from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import os
from datetime import datetime, timedelta, timezone
import time
import json
import logging
import asyncio

# Keep server alive
from flask import Flask
from threading import Thread

web_app = Flask('')

@web_app.route('/')
def home():
    return "✅ Bot is running."

@web_app.route('/health')
def health():
    return "OK", 200

def run_web():
    web_app.run(host='0.0.0.0', port=8080)

Thread(target=run_web).start()
# end keep server alive

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('goatcounter_bot.log')
    ]
)
logger = logging.getLogger('goatcounter_bot')

# Suppress httpx INFO logs
logging.getLogger('httpx').setLevel(logging.WARNING)

# Environment variables (use Replit secrets)
GOAT_SITE = os.getenv("GOAT_SITE")  # e.g., uybinh3
GOAT_API_KEY = os.getenv("GOAT_API_KEY")  # Your GoatCounter API key
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")  # Your Telegram Bot Token

# Base URL for the GoatCounter API
GOAT_BASE_URL = f"https://{GOAT_SITE}.goatcounter.com/api/v0"

async def check_rate_limit(response):
    """Check rate limit headers and return seconds to wait if exceeded"""
    limit = int(response.headers.get('X-Rate-Limit-Limit', 4))
    remaining = int(response.headers.get('X-Rate-Limit-Remaining', 4))
    reset = int(response.headers.get('X-Rate-Limit-Reset', 0))

    if remaining <= 0:
        return reset
    return 0

async def make_api_request(url, params, headers, max_retries=3):
    """Make API request with retry logic for rate limits"""
    endpoint = url.replace(GOAT_BASE_URL, '')
    logger.info(f"Fetching data from GoatCounter API: {endpoint} with params: {params}")

    for attempt in range(max_retries):
        try:
            logger.info(f"API request attempt {attempt+1}/{max_retries}")
            response = requests.get(url, params=params, headers=headers)
            wait_time = await check_rate_limit(response)

            if wait_time > 0:
                logger.warning(f"Rate limit exceeded. Waiting {wait_time} seconds before retry.")
                await asyncio.sleep(wait_time)
                continue

            response.raise_for_status()
            data = response.json()

            if 'error' in data or 'errors' in data:
                error_msg = data.get('error', json.dumps(data.get('errors', 'Unknown error')))
                logger.error(f"API error: {error_msg}")
                raise Exception(f"API error: {error_msg}")

            logger.info(f"Successfully fetched data from {endpoint}")
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception: {str(e)}")
            if attempt == max_retries - 1:
                raise
            logger.info(f"Retrying in 1 second...")
            await asyncio.sleep(1)  # Wait before retry

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Set date range to last 24 hours, rounded to the hour
        now = datetime.now().replace(minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        end = now
        start = end - timedelta(hours=24)
        params = {
            "start": start.strftime("%Y-%m-%dT%H:00:00Z"),
            "end": end.strftime("%Y-%m-%dT%H:00:00Z"),
            "limit": 100
        }

        # Use Bearer auth as per documentation
        headers = {
            "Authorization": f"Bearer {GOAT_API_KEY}",
            "Content-Type": "application/json"
        }

        # Make the API request
        data = await make_api_request(f"{GOAT_BASE_URL}/stats/hits", params, headers)

        # Calculate totals from hits
        total_pageviews = sum(hit.get('count', 0) for hit in data.get('hits', []))
        total_visitors = sum(1 for hit in data.get('hits', []) if hit.get('is_unique', False))

        # Create the main message
        message = (
            f"📈 GoatCounter Stats for {start.strftime('%Y-%m-%d %H:00')} to {end.strftime('%Y-%m-%d %H:00')} UTC:\n\n"
            f"👥 Unique visitors: {total_visitors}\n"
            f"📄 Total pageviews: {total_pageviews}\n"
        )

        # Add top paths if available
        if data.get('hits') and len(data['hits']) > 0:
            message += "\n📊 Top pages:\n"
            path_counts = {}
            for hit in data['hits']:
                path = hit.get('path', 'Unknown')
                path_counts[path] = path_counts.get(path, 0) + hit.get('count', 0)
            for i, (path, views) in enumerate(sorted(path_counts.items(), key=lambda x: x[1], reverse=True)[:5], 1):
                message += f"{i}. {path}: {views} views\n"

        await update.message.reply_text(message)

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def weekly_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Set date range to last 7 days, rounded to the hour
        now = datetime.now().replace(minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        end = now
        start = end - timedelta(days=7)
        params = {
            "start": start.strftime("%Y-%m-%dT%H:00:00Z"),
            "end": end.strftime("%Y-%m-%dT%H:00:00Z"),
            "limit": 100
        }

        # Use Bearer auth as per documentation
        headers = {
            "Authorization": f"Bearer {GOAT_API_KEY}",
            "Content-Type": "application/json"
        }

        # Make the API request
        data = await make_api_request(f"{GOAT_BASE_URL}/stats/hits", params, headers)

        # Calculate totals from hits
        total_pageviews = sum(hit.get('count', 0) for hit in data.get('hits', []))
        total_visitors = sum(1 for hit in data.get('hits', []) if hit.get('is_unique', False))

        # Create the main message
        message = (
            f"📈 GoatCounter Weekly Stats for {start.strftime('%Y-%m-%d %H:00')} to {end.strftime('%Y-%m-%d %H:00')} UTC:\n\n"
            f"👥 Unique visitors: {total_visitors}\n"
            f"📄 Total pageviews: {total_pageviews}\n"
        )

        # Add top paths if available
        if data.get('hits') and len(data['hits']) > 0:
            message += "\n📊 Top pages this week:\n"
            path_counts = {}
            for hit in data['hits']:
                path = hit.get('path', 'Unknown')
                path_counts[path] = path_counts.get(path, 0) + hit.get('count', 0)
            for i, (path, views) in enumerate(sorted(path_counts.items(), key=lambda x: x[1], reverse=True)[:5], 1):
                message += f"{i}. {path}: {views} views\n"

        await update.message.reply_text(message)

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

def main():
    # Initialize the bot
    app = ApplicationBuilder().token(TG_BOT_TOKEN).build()

    # Add command handlers
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("weekly", weekly_stats))

    # Start the bot
    logger.info("🚀 GoatCounter Stats Bot is running...")
    logger.info("Available commands:")
    logger.info("  /stats - Get last 24 hours statistics")
    logger.info("  /weekly - Get statistics for the past week")
    app.run_polling()

if __name__ == "__main__":
    main()