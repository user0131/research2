from flask import Flask
from flask_cors import CORS
from openai import OpenAI
import os
import logging
from dotenv import load_dotenv
from routes.main import register_routes

# Load environment variables from .env file
load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# OpenAI API設定
client = None

def get_openai_client():
    global client
    if client is None:
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        client = OpenAI(api_key=api_key)
    return client

# ルートを登録
register_routes(app, get_openai_client)

if __name__ == '__main__':
    debug = os.environ.get('FLASK_ENV', 'production') == 'development'
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=debug, host=host, port=port) 