"""
APIルート定義
Flaskのルートエンドポイントを管理
"""

from flask import request, jsonify
from command_controller import command_controller
import logging

logger = logging.getLogger(__name__)


def register_routes(app, get_openai_client):
    """Flaskアプリにルートを登録"""
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """ヘルスチェック"""
        result = command_controller.health_check()
        return jsonify(result)
    
    # 旧システム用エンドポイント（後で削除予定）
    
    @app.route('/api/process_logs', methods=['POST'])
    def process_logs():
        """ログを処理してコマンドを決定（旧システム用）"""
        try:
            data = request.get_json()
            openai_client = get_openai_client()
            result = command_controller.process_logs(data, openai_client)
            
            status_code = 400 if not result.get("success", True) else 200
            return jsonify(result), status_code
            
        except Exception as e:
            logger.error(f"Error in process_logs route: {str(e)}")
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
            
            result = command_controller.get_logs(page, per_page)
            
            if "error" in result:
                return jsonify(result), 500
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in get_logs route: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/logs/stats', methods=['GET'])
    def get_log_stats():
        """ログ統計を取得"""
        try:
            result = command_controller.get_log_stats()
            
            if "error" in result:
                return jsonify(result), 500
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in get_log_stats route: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/task_status', methods=['GET'])
    def get_task_status():
        """タスクの状況を取得"""
        try:
            result = command_controller.get_task_status()
            
            if "error" in result:
                return jsonify(result), 500
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in get_task_status route: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/logs/clear', methods=['POST'])
    def clear_logs():
        """ログをクリア"""
        try:
            result = command_controller.clear_logs()
            
            if "error" in result:
                return jsonify(result), 500
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in clear_logs route: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/logs/export', methods=['GET'])
    def export_logs():
        """ログをエクスポート"""
        try:
            result = command_controller.export_logs()
            
            if "error" in result:
                return jsonify(result), 500
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in export_logs route: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/logs/context', methods=['GET'])
    def get_log_context():
        """ログコンテキストを取得"""
        try:
            result = command_controller.get_log_context()
            
            if "error" in result:
                return jsonify(result), 500
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in get_log_context route: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    # 新しいAPIフロー用エンドポイント
    
    @app.route('/api/plan', methods=['POST'])
    def plan_task():
        """タスク計画: LLMでタスクをステップに分解してキューに追加"""
        try:
            data = request.get_json()
            openai_client = get_openai_client()
            result = command_controller.plan_task(data, openai_client)
            
            status_code = 400 if not result.get("success", True) else 200
            return jsonify(result), status_code
            
        except Exception as e:
            logger.error(f"Error in plan_task route: {str(e)}")
            return jsonify({
                "success": False,
                "error": f"エラーが発生しました: {str(e)}"
            }), 500
    
    @app.route('/api/next-step', methods=['GET'])
    def get_next_step():
        """次のステップ取得"""
        try:
            result = command_controller.get_next_step()
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in get_next_step route: {str(e)}")
            return jsonify({
                "has_step": False,
                "error": f"エラーが発生しました: {str(e)}"
            }), 500
    
    @app.route('/api/step/<step_id>/complete', methods=['POST'])
    def complete_step(step_id):
        """ステップ完了通知とLLM2による判定"""
        try:
            data = request.get_json()
            openai_client = get_openai_client()
            result = command_controller.complete_step(step_id, data, openai_client)
            
            status_code = 400 if not result.get("success", True) else 200
            return jsonify(result), status_code
            
        except Exception as e:
            logger.error(f"Error in complete_step route: {str(e)}")
            return jsonify({
                "success": False,
                "error": f"エラーが発生しました: {str(e)}"
            }), 500
    
    @app.route('/api/event', methods=['POST'])
    def handle_event():
        """エラー時やイベント時の処理"""
        try:
            data = request.get_json()
            openai_client = get_openai_client()
            result = command_controller.handle_event(data, openai_client)
            
            status_code = 400 if not result.get("success", True) else 200
            return jsonify(result), status_code
            
        except Exception as e:
            logger.error(f"Error in handle_event route: {str(e)}")
            return jsonify({
                "success": False,
                "error": f"エラーが発生しました: {str(e)}"
            }), 500