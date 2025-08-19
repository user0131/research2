FROM python:3.9-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムパッケージのアップデート
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 依存関係ファイルをコピー
COPY requirements.txt .

# Python パッケージをインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# ポートを公開
EXPOSE 5000

# 環境変数を設定
ENV FLASK_APP=src/app.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app/src

# アプリケーションを起動（srcディレクトリ内のapp.pyを参照）
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "300", "--workers", "1", "src.app:app"] 