# Unity-LLM Backend

Unity ゲームプロジェクト用のLLMバックエンドサービスです。

## 概要

このサービスは、UnityからのゲームログをOpenAI GPT-4o-miniを使って分析し、次に実行すべきコマンドを決定します。

## セットアップ

### 1. 環境変数の設定

プロジェクトルートに `.env` ファイルを作成し、以下の環境変数を設定してください：

```bash
# OpenAI API Key
OPENAI_API_KEY=sk-your-openai-api-key-here

# Flask環境設定
FLASK_ENV=development
FLASK_DEBUG=True

# サーバー設定
HOST=0.0.0.0
PORT=5000
```

### 2. Dockerを使用した起動

```bash
# Dockerコンテナをビルドして起動
cd ./backend && docker-compose down

# バックグラウンドで実行
cd ./backend && docker-compose up -d --build
```

## API エンドポイント

### ヘルスチェック
```
GET /api/health
```

### ログ処理
```
POST /api/process_logs
Content-Type: application/json

{
  "logs": ["ログ1", "ログ2", "..."]
}
```

### LLMテスト
```
POST /api/test_llm
Content-Type: application/json

{
  "message": "テストメッセージ"
}
```

### ログ管理エンドポイント

#### ログクリア
```
POST /api/logs/clear
curl -X POST http://localhost:5000/api/logs/clear
```
### タスクリセット
```
curl -X POST http://localhost:5000/api/tasks/reset
```

#### 最近のログ取得
```
GET /api/logs/recent?count=10
```
最近のログエントリを取得します。`count`パラメータで取得数を指定できます（デフォルト: 10）。

#### ログ統計情報
```
GET /api/logs/statistics
```
ログの統計情報を取得します。

#### 特定タスクのログ
```
GET /api/logs/task/{task_id}
```
特定のタスクIDに関連するログを取得します。

#### タスク進捗状況
```
GET /api/logs/progress
```
現在のタスクの進捗状況を取得します。

## ログ管理

### ログファイルの保存場所
ログは `game_logs.json` ファイルに保存されます。

### ログクリアの方法

#### 1. APIエンドポイントを使用（推奨）
```bash
# cURLを使用
curl -X POST http://localhost:5000/api/logs/clear

# または、Dockerコンテナが起動している場合
docker-compose exec backend curl -X POST http://localhost:5000/api/logs/clear
```

#### 2. ファイルを直接削除
```bash
# ログファイルを削除
rm game_logs.json

# または、Dockerコンテナ内で削除
docker-compose exec backend rm game_logs.json
```

#### 3. Dockerコンテナを再起動
```bash
# コンテナを停止して再起動（データをクリア）
docker-compose down
docker-compose up -d --build
```

### ログの確認方法

#### 最近のログを確認
```bash
curl http://localhost:5000/api/logs/recent?count=5
```

#### ログ統計を確認
```bash
curl http://localhost:5000/api/logs/statistics
```

## 利用可能なコマンド

- `north`: 北へ移動
- `south`: 南へ移動
- `east`: 東へ移動
- `west`: 西へ移動
- `pickup`: アイテムを拾う/置く (Zキー相当)
- `interact`: TVなどと相互作用 (Eキー相当)
- `wait`: 待機

## 使用方法

1. Unity側でゲームログを収集
2. `/api/process_logs` エンドポイントにログを送信
3. バックエンドがLLMでコマンドを決定
4. Unity側でコマンドを実行

## 注意事項

- OpenAI API キーが必要です
- インターネット接続が必要です
- APIの使用量に注意してください
- ログファイルは自動的に最新100エントリまで保持されます 



## 開発メモ
-やること
 --NavMeshAgentを用いて、対象オブジェクトへの移動を円滑化
-使用想定コマンド
 --移動する場所を指定して移動するコマンド
 --pick, push
-アーキテクト
 --今の状況をもとに、実施するタスク(ステップ詳細に分かれる)内容を決定するLLM
 --キューにステップ(コマンド付き)を入れる
 --frontendから、stepごとに完了の連絡を入れ、完了の連絡が入るごとに次のステップ(コマンド)を送る
 --「error」や「attention」(会話やイベント発生)ごとに、今のstepをそのまま進めるか、別のタスクを決定するかを決めるLLM

-他
 --ファイルを分割してアップロードする。


 --僕は、「データがバックエンドに送信さ
  れると、そのログの内容+エージェントの目的(固定)」をもとにタスクのste
  p（コマンド）を決めるLLMファイル, 
  その出力の内容をキューとして保存するファイル, フロントからの内容 
  infoやerrorやattention(HTTPヘッダの内容)をもとに、「LLMにもう一度考
  えさせるか, キューの次のstep(コマンド)を渡すか決定するapp.py(ここはi
  f文で分岐)」がメインであればいいと思っています。

シンプルな5ファイル
  /backend/src/
  ├── app.py                 # 統合されたAPI
  ├── task_planner.py        # タスク分解LLM
  ├── queue_manager.py       # キュー管理
  ├── config.py             # 設定　
  └── storage/
      └── queue.json        # キューデータ

    
  新しいワークフロー

  1. Unity → /api/plan: 状況送信、タスク計画要求
  2. Backend: LLMがタスクをステップに分解、キューに追加
  3. Unity → /api/next-step: 次のステップ取得
  4. Unity: ステップ実行（NavMeshAgent移動、pickup等）
  5. Unity → /api/step/<id>/complete: 完了通知
  6. Backend: 次のステップを返す（3に戻る）
  7. エラー時 → /api/event: LLMが継続/再計画を判断


タスクをステップに分解するとき、もう少し工夫してもいいと思う。LLMが、次にやるタスクとそのstepを決める際に、
来たログ(現在の状況)と、これまでのログの内容(これ必要?必要だとしたら、「これまでやってきたこと」の記憶領域として必要)、そしてコマンドの実行例をいくつか(できることマニュアルを規定する)(今後fine-tuningでもいいかも)
そして、エージェントとしての目的(これは、現段階では以下のような感じ
"""
あなたの目的は、研究室を準備するための４つのタスクを完了することです。
１つは、

そして、〇〇です。
""")

のデータを渡して、
