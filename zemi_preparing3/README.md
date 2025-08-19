# Unity LLM Game Controller

UnityゲームをLLM（GPT-4o-mini）で自動操作するシステムです。

## 概要

このプロジェクトは、Unityで作成されたゲームを人工知能が自動で操作できるようにするシステムです。ゲーム内の状況をLLMが分析し、次に実行すべきアクションを決定して自動実行します。

### システム構成

```
Unity Game (フロントエンド)
    ↓ ゲーム状況ログ
Flask Backend (バックエンド)
    ↓ LLM分析
OpenAI GPT-4o-mini
    ↓ コマンド決定
Unity Game (コマンド実行)
```

## 機能

- **自動ゲーム操作**: プレイヤーの代わりにLLMがゲームを操作
- **状況分析**: ゲーム内の状況を理解してコンテキストに応じた行動を選択
- **リアルタイム制御**: ゲーム進行に合わせてリアルタイムでコマンドを決定
- **デバッグ機能**: 詳細なログとGUIでの状態監視

### 対応コマンド

- `north/south/east/west`: 移動コマンド
- `pickup`: アイテムの拾取/配置
- `interact`: オブジェクトとの相互作用
- `wait`: 待機

## セットアップ手順

### 前提条件

- Docker & Docker Compose
- Unity 2022.3 以降
- OpenAI API アカウント

### 1. 環境変数の設定

プロジェクトルートに `.env` ファイルを作成：

```bash
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### 2. バックエンドの起動

```bash
# Docker Composeでバックエンドを起動
docker-compose up --build

# または直接Pythonで実行（開発用）
cd backend
pip install -r requirements.txt
python app.py
```

### 3. Unityプロジェクトの設定

1. Unity で `zemi_preparing3` プロジェクトを開く
2. `PlayerArmature` プレハブに以下のコンポーネントを追加：
   - `LLMCommunicator`
   - `CommandExecutor` 
   - `LLMGameController`

3. `LLMGameController` の設定：
   - Backend URL: `http://localhost:5000`
   - Enable LLM Control: `true`

### 4. システムのテスト

```bash
# バックエンドのテスト
cd backend
python test_integration.py

# ヘルスチェック
curl http://localhost:5000/api/health
```

## 使用方法

### 基本的な流れ

1. **バックエンド起動**: Dockerまたは直接Pythonで起動
2. **Unity実行**: Unityでゲームを開始
3. **LLM制御開始**: ゲーム内でLLM制御が自動開始
4. **監視**: GUIまたはログでLLMの動作を監視

### デバッグ機能

#### Unity内GUI
ゲーム実行中に左上にデバッグパネルが表示されます：

- **Status**: LLM制御の状態
- **Backend**: バックエンド接続状態
- **Commands Executed**: 実行されたコマンド数
- **Toggle LLM Control**: LLM制御のON/OFF
- **Emergency Stop**: 緊急停止

#### ログ出力
コンソールに詳細なログが出力されます：

```
[LLMGameController] Initialized successfully
[LLMCommunicator] Backend connection established
[CommandExecutor] Executing command: north - プレイヤーが北に移動すべき
```

### API エンドポイント

#### ヘルスチェック
```bash
curl http://localhost:5000/api/health
```

#### ログ処理（Unity側から自動送信）
```bash
curl -X POST http://localhost:5000/api/process_logs \
  -H "Content-Type: application/json" \
  -d '{"logs": ["[Narrator] === 現在の状況 ===", "..."]}'
```

## プロジェクト構成

```
.
├── README.md
├── docker-compose.yaml
├── backend/
│   ├── app.py                 # Flask メインアプリケーション
│   ├── requirements.txt       # Python依存関係
│   ├── Dockerfile
│   ├── test_integration.py    # 統合テスト
│   └── README.md
└── zemi_preparing3/           # Unity プロジェクト
    └── Assets/
        └── C#/
            ├── LLMCommunicator.cs      # バックエンド通信
            ├── CommandExecutor.cs      # コマンド実行
            ├── LLMGameController.cs    # メイン制御
            └── AccessibilityNarrator.cs # 状況報告（既存）
```

## トラブルシューティング

### バックエンド接続エラー

```
[LLMCommunicator] Backend connection failed
```

**解決方法**:
1. バックエンドが起動しているか確認
2. ポート5000が使用可能か確認
3. ファイアウォール設定を確認

### OpenAI API エラー

```
[LLMCommunicator] LLM Error: Invalid API key
```

**解決方法**:
1. `.env` ファイルのAPI키が正しいか確認
2. OpenAIアカウントのクレジット残高を確認
3. API使用制限を確認

### Unity コンポーネントエラー

```
[LLMGameController] Required components not found!
```

**解決方法**:
1. PlayerArmatureに必要なコンポーネントが追加されているか確認
2. スクリプトにコンパイルエラーがないか確認
3. AccessibilityNarratorが正しく設定されているか確認

## カスタマイズ

### LLMプロンプトの変更

`backend/app.py` の `system_prompt` を編集してLLMの動作を調整できます。

### コマンドの追加

1. `backend/app.py`: 新しいコマンドをシステムプロンプトに追加
2. `CommandExecutor.cs`: 新しいコマンドの実行ロジックを追加

### ログ処理の調整

`LLMGameController.cs` で以下を調整可能：
- `logCheckInterval`: ログチェック間隔
- `maxLogHistory`: 保持するログ数
- ログフィルタリングロジック

## 貢献

プルリクエストや課題報告をお待ちしています。

## 注意事項

- OpenAI APIの使用料金にご注意ください
- LLMの応答時間によりゲームの動作が遅くなる場合があります
- ネットワーク接続が必要です 