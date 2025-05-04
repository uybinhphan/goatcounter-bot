from flask import Flask
from threading import Thread

# Start a simple web server to keep Replit alive
web_app = Flask('')

@web_app.route('/')
def home():
    return "✅ Bot is running."

def run_web():
    web_app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run_web).start()
