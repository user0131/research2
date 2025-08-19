from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os
import logging
from datetime import datetime
from llm_command_decider import LLMCommandDecider
from storage import storage
from task_definitions import (
    get_goal, get_tasks, get_dependencies, 
    get_task_description, get_task_dependencies,
    get_task_examples, get_task_example
)

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# OpenAI API設定（遅延初期化）
client = None

def get_openai_client():
    global client
    if client is None:
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        client = OpenAI(api_key=api_key)
    return client

# インスタンス生成
command_decider = LLMCommandDecider()

@app.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "message": "API is running"})

@app.route('/api/process_logs', methods=['POST'])
def process_logs():
    """ログを処理してコマンドを決定"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "command": "wait", "reasoning": "無効なリクエスト形式"}), 400
        
        logs = data.get('logs', [])
        
        if not logs:
            return jsonify({"success": False, "command": "wait", "reasoning": "ログが提供されていません"}), 400
        
        # OpenAIクライアントを取得
        openai_client = get_openai_client()
        
        # 過去のログコンテキストを取得
        log_context = storage.get_context_for_llm(logs)
        
        # LLMでコマンドを決定（新しい3段階システム）
        result = command_decider.analyze_logs_and_decide(logs, openai_client, log_context)
        
        # ログエントリを保存
        storage.add_log_entry(
            logs=logs,
            command=result["command"],
            reasoning=result["reasoning"],
            current_task=result.get("current_task", "unknown"),
            progress=result.get("progress", "不明")
        )
        
        # ログに記録
        logger.info(f"Command decided: {result['command']} - {result['reasoning']}")
        
        # Unity用のレスポンス形式で返す
        return jsonify({
            "success": result.get("success", True),
            "command": result["command"],
            "reasoning": result["reasoning"],
            "current_task": result.get("current_task", "unknown"),
            "progress": result.get("progress", "不明"),
            "current_group": result.get("current_group", "unknown"),
            "group_progress": result.get("group_progress", None)
        })
        
    except Exception as e:
        logger.error(f"Error processing logs: {str(e)}")
        return jsonify({
            "success": False,
            "command": "wait",
            "reasoning": f"エラーが発生しました: {str(e)}"
        }), 500

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """ログ履歴を取得"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        logs = storage.get_recent_commands(count=per_page)
        
        return jsonify({
            "logs": logs,
            "page": page,
            "per_page": per_page,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting logs: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs/stats', methods=['GET'])
def get_log_stats():
    """ログ統計を取得"""
    try:
        stats = storage.get_statistics()
        return jsonify({
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting log stats: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/task_status', methods=['GET'])
def get_task_status():
    """タスクの状況を取得（細分化されたタスク対応）"""
    try:
        # タスク定義情報を取得
        dependencies = get_dependencies()
        tasks = get_tasks()
        goal = get_goal()
        
        return jsonify({
            "goal": goal,
            "tasks": tasks,
            "dependencies": dependencies,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs/clear', methods=['POST'])
def clear_logs():
    """ログをクリア"""
    try:
        storage.clear_all()
        return jsonify({
            "message": "ログがクリアされました",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error clearing logs: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs/export', methods=['GET'])
def export_logs():
    """ログをエクスポート"""
    try:
        export_data = storage.export_data()
        return jsonify({
            "export_data": export_data,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error exporting logs: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs/context', methods=['GET'])
def get_log_context():
    """ログコンテキストを取得"""
    try:
        context = storage.get_context_for_llm()
        return jsonify({
            "context": context,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting log context: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs/progress', methods=['GET'])
def get_task_progress():
    """タスクの進捗状況を取得"""
    try:
        # タスクの進捗は新しいシステムでは不要
        progress = {"message": "Task progress moved to new system"}
        return jsonify({
            "progress": progress,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting task progress: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/progress', methods=['GET'])
def get_task_progress_new():
    """新しいタスク管理システムの進捗状況を取得（細分化対応）"""
    try:
        progress = get_task_progress_summary()
        next_task = get_next_available_task()
        current_group = get_current_task_group()
        group_progress = get_task_group_progress(current_group) if current_group != "completed" else None
        
        return jsonify({
            "progress": progress,
            "next_task": next_task,
            "current_group": current_group,
            "group_progress": group_progress,
            "task_breakdown": {
                "tv_operation": get_task_group_progress("tv_operation"),
                "chair_movement": get_task_group_progress("chair_movement"),
                "plate_movement": get_task_group_progress("plate_movement"),
                "pc_placement": get_task_group_progress("pc_placement")
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting task progress: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/reset', methods=['POST'])
def reset_tasks():
    """すべてのタスクをリセット（デバッグ用）"""
    try:
        reset_all_tasks()
        return jsonify({
            "message": "すべてのタスクがリセットされました",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error resetting tasks: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/complete/<task_id>', methods=['POST'])
def complete_task(task_id):
    """タスクを手動で完了状態にマーク（デバッグ用）"""
    try:
        mark_task_completed(task_id)
        progress = get_task_progress_summary()
        current_group = get_current_task_group()
        group_progress = get_task_group_progress(current_group) if current_group != "completed" else None
        
        return jsonify({
            "message": f"タスク {task_id} が完了としてマークされました",
            "progress": progress,
            "current_group": current_group,
            "group_progress": group_progress,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error completing task: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/groups', methods=['GET'])
def get_task_groups():
    """タスクグループの詳細情報を取得"""
    try:
        groups = {
            "tv_operation": get_task_group_progress("tv_operation"),
            "chair_movement": get_task_group_progress("chair_movement"),
            "plate_movement": get_task_group_progress("plate_movement"),
            "pc_placement": get_task_group_progress("pc_placement")
        }
        
        current_group = get_current_task_group()
        
        return jsonify({
            "groups": groups,
            "current_group": current_group,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting task groups: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 