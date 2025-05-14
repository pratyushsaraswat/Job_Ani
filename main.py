import threading
from flask import Flask
import sys
import os

# Ensure src is in the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "src", "bot"))

# Import your Telegram bot main function
from telegram_bot import main as telegram_main

app = Flask(__name__)

@app.route("/")
def index():
    return "JobANI Flask app is running!"

def run_telegram_bot():
    telegram_main()

# Start the Telegram bot in a background thread
threading.Thread(target=run_telegram_bot, daemon=True).start()

# This is the WSGI entrypoint for gunicorn
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)