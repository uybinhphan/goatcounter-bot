from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import os
from datetime import datetime, timedelta
import time
import json

# Keep server alive by running a simple web server
from flask import Flask
from threading import Thread

# Start a simple web server to keep Replit alive
web_app = Flask('')

@web_app.route('/')
def home():
    return "✅ Bot is running."

def run_web():
    web_app.run(host='0.0.0.0', port=8080)

Thread(target=run_web).start()
# end keep server alive

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
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers)
            wait_time = await check_rate_limit(response)

            if wait_time > 0:
                await asyncio.sleep(wait_time)
                continue

            response.raise_for_status()
            data = response.json()

            if 'error' in data or 'errors' in data:
                error_msg = data.get('error', json.dumps(data.get('errors', 'Unknown error')))
                raise Exception(f"API error: {error_msg}")

            return data

        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(1)  # Wait before retry

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Get today's date and format it as YYYY-MM-DD
        today = datetime.now().strftime("%Y-%m-%d")

        # Set up API request
        url = f"{GOAT_BASE_URL}/stats/hits"

        # Parameters for the request
        params = {
            "start": today,
            "end": today,
            "limit": 5
        }

        # Headers with authentication
        headers = {
            "Authorization": f"Bearer {GOAT_API_KEY}",
            "Content-Type": "application/json"
        }

        # Make the API request
        data = await make_api_request(url, params, headers)

        # Extract the overall stats
        total_pageviews = data.get('total_count', 0)
        total_visitors = data.get('total_unique', 0)

        # Create the main message
        message = (
            f"📈 GoatCounter Stats for {today}:\n\n"
            f"👥 Unique visitors: {total_visitors}\n"
            f"📄 Total pageviews: {total_pageviews}\n"
        )

        # Add top pages if available
        if data.get('paths') and len(data['paths']) > 0:
            message += "\n📊 Top pages today:\n"
            for i, page in enumerate(data['paths'], 1):
                path = page.get('path', 'Unknown')
                views = page.get('count', 0)
                uniques = page.get('count_unique', 0)
                message += f"{i}. {path}: {views} views ({uniques} unique)\n"

        await update.message.reply_text(message)

    except requests.exceptions.RequestException as e:
        await update.message.reply_text(f"❌ API Error: {str(e)}")
    except KeyError as e:
        await update.message.reply_text(f"❌ Data structure error: {str(e)}")
    except Exception as e:
        await update.message.reply_text(f"❌ Unexpected error: {str(e)}")

async def weekly_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Get date range (last 7 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        # Format dates as YYYY-MM-DD
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        # Set up API request
        url = f"{GOAT_BASE_URL}/stats/hits"

        # Parameters for the request
        params = {
            "start": start_str,
            "end": end_str,
            "limit": 5
        }

        # Headers with authentication
        headers = {
            "Authorization": f"Bearer {GOAT_API_KEY}",
            "Content-Type": "application/json"
        }

        # Make the API request
        data = await make_api_request(url, params, headers)

        # Extract the overall stats
        total_pageviews = data.get('total_count', 0)
        total_visitors = data.get('total_unique', 0)

        # Create the main message
        message = (
            f"📈 GoatCounter Weekly Stats ({start_str} to {end_str}):\n\n"
            f"👥 Unique visitors: {total_visitors}\n"
            f"📄 Total pageviews: {total_pageviews}\n"
        )

        # Add top pages if available
        if data.get('paths') and len(data['paths']) > 0:
            message += "\n📊 Top pages this week:\n"
            for i, page in enumerate(data['paths'], 1):
                path = page.get('path', 'Unknown')
                views = page.get('count', 0)
                uniques = page.get('count_unique', 0)
                message += f"{i}. {path}: {views} views ({uniques} unique)\n"

        await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

def main():
    # Initialize the bot
    app = ApplicationBuilder().token(TG_BOT_TOKEN).build()

    # Add command handlers
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("weekly", weekly_stats))

    # Start the bot
    print("🚀 GoatCounter Stats Bot is running...")
    print("Available commands:")
    print("  /stats - Get today's statistics")
    print("  /weekly - Get statistics for the past week")
    app.run_polling()
    
if __name__ == "__main__":
    main()