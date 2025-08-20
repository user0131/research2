# Unity Research Lab Backend

Unity研究室シミュレーション用の統合LLMバックエンドサービスです。

## 概要

このサービスは、Unity研究室環境からのログを3つのLLMシステムで分析し、研究室準備タスクの自動化を実現します：
- **Task & Step Planner LLM**: 状況分析とタスクステップ分解
- **Step Completion Checker LLM**: ステップ完了判定と進行制御
- **Task Reconstructor LLM**: エラー時のタスク再構成

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

### 統合プロセシングエンドポイント
```
POST /api/process
Content-Type: application/json

{
  "logs": ["現在の状況ログ"],
  "step_id": "実行完了ステップID (オプション)",
  "execution_result": "実行結果 (オプション)"
}
```

**レスポンス形式:**
```json
{
  "success": true,
  "command": "navigate",
  "x": 0.1,
  "z": 5.4,
  "reasoning": "テレビに隣接してinteractコマンドが使用可能になる",
  "current_task": "task_20250120_143052",
  "step_id": "uuid-generated-step-id"
}
```

### ヘルスチェック
```
GET /api/health
```

## アーキテクチャ

### ファイル構成
```
/backend/src/
├── app.py                 # Flaskアプリケーション
├── routes.py              # API ルート定義
├── command_controller.py  # 統合プロセス制御
├── llm_manager.py         # 3つのLLMシステム管理
├── step_manager.py        # ステップキュー管理
├── storage_manager.py     # ログ・データ保存
└── constants.py           # タスク定義・設定値
```

### 処理フロー
1. **状況分析**: Unity→ `/api/process` でログ送信
2. **アルゴリズム判定**: エラー検出、キュー状態分析
3. **LLM処理**: 
   - 初回時: Task Planner がステップ分解
   - 完了時: Completion Checker が判定
   - エラー時: Task Reconstructor が再構成
4. **レスポンス**: Unity形式でコマンド返却
5. **ログ記録**: コマンド-ログペア保存

### ログ管理
- **保存場所**: `log_file.json`
- **保存形式**: コマンド-ログペア (最大100レコード)
- **自動ローテーション**: 最新100件を保持

## 利用可能なコマンド

- **`navigate`**: 絶対座標への移動 (parameters: x, z)
- **`pickup`**: アイテムの拾い上げ/設置
- **`interact`**: オブジェクトとの相互作用 (TV電源など)
- **`wait`**: 待機

## 研究室タスク

### 目標
研究室の準備：テレビをONにし、椅子とPCプレートを適切な場所に移動し、PCをプレート上に配置する

### タスク一覧
1. **tv_switch**: テレビの電源をONにする
2. **chair_move**: 椅子をChairAreaに移動する
3. **pc_plate_move**: PCプレートをDaiAreaに移動する
4. **put_pc_on_plate**: PCをプレート上に配置する

### 依存関係
- `put_pc_on_plate` は `pc_plate_move` の完了が必要
- 他のタスクは並行実行可能

## 使用方法

1. Unity側で状況ログを収集
2. `/api/process` エンドポイントにログを送信
3. バックエンドが3つのLLMで処理を決定
4. Unity側で返されたコマンドを実行
5. 実行結果を再度 `/api/process` に送信（完了通知）

## 注意事項

- OpenAI API キーが必要です
- インターネット接続が必要です  
- APIの使用量に注意してください
- ログファイルは自動的に最新100エントリまで保持されます
- Y座標は自動で0に設定されます（必要に応じて変更可能）

## 開発履歴

### v2.0 - 統合LLMシステム
- 3つのLLMシステム統合 (Planner, Checker, Reconstructor)
- 単一エンドポイント `/api/process` による統合処理
- 絶対座標ナビゲーションシステム
- エラー時自動再構成機能
- ステップキュー管理システム

### アーキテクチャ変更
- 旧: 複数エンドポイント → 新: 単一統合エンドポイント
- 旧: 方向指定移動 → 新: 絶対座標移動
- 旧: 手動エラー処理 → 新: 自動エラー検出・再構成



タスクをステップに分解するとき、もう少し工夫してもいいと思う。LLMが、次にやるタスクとそのstepを決める際に、
来たログ(現在の状況)と、これまでのログの内容(これ必要?必要だとしたら、「これまでやってきたこと」の記憶領域として必要)、そしてコマンドの実行例をいくつか(できることマニュアルを規定する)(今後fine-tuningでもいいかも)
そして、エージェントとしての目的(これは、現段階では以下のような感じ
"""
あなたの目的は、研究室を準備するための４つのタスクを完了することです。
１つは、

そして、〇〇です。
""")

のデータを渡して、
