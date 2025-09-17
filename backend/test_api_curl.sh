#!/bin/bash

# バックエンドAPIのテストスクリプト
# 使用方法: ./test_api_curl.sh

echo "=== Backend API Test ==="
echo ""

# 1. ヘルスチェック
echo "1. Health Check:"
curl -X GET http://localhost:5000/api/health
echo -e "\n"

# 2. Process API - 初回リクエスト（タスクの設定）
echo "2. Process API - Set Task:"
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{
    "current_task": "箱を積み上げる",
    "step_id": null,
    "x": 0,
    "y": 0,
    "z": 0,
    "result": null,
    "logs": ["タスク: 箱を3個積み上げる", "現在の状態: 箱が床に3個置かれている"]
  }'
echo -e "\n"

# 3. Process API - ステップ実行の例
echo "3. Process API - Execute Step:"
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{
    "current_task": "箱を積み上げる",
    "step_id": "step_1",
    "x": 10,
    "y": 5,
    "z": 0,
    "result": "移動完了",
    "logs": ["移動が完了しました"]
  }'
echo -e "\n"

# 4. Process API - エラーケースのテスト
echo "4. Process API - Error Case (empty body):"
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{}'
echo -e "\n"