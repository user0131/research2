from flask import Flask
from flask_cors import CORS
from openai import OpenAI
import os
import logging
from routes.main import register_routes

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
    app.run(debug=True, host='0.0.0.0', port=5000) 