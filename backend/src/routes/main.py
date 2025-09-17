"""
APIルート定義
Flaskのルートエンドポイントを管理
"""

from flask import request, jsonify
from services.command_controller import command_controller
import logging

logger = logging.getLogger(__name__)


def register_routes(app, get_openai_client):
    
    # === ヘルスチェック ===
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        result = command_controller.health_check()
        return jsonify(result)
    
    # === 統合処理エンドポイント ===
    
    @app.route('/api/process', methods=['POST', 'OPTIONS'])
    def process():
        # CORS プリフライトリクエスト対応
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            data = request.get_json()
            
            # 入力データの基本検証
            if data is None:
                return _create_error_response("JSONデータが無効です"), 400
            
            openai_client = get_openai_client()
            
            # リクエスト情報をログに記録
            logger.debug(f"Processing request with data keys: {list(data.keys()) if data else 'None'}")
            
            result = command_controller.process_step(data, openai_client)
            
            # レスポンス情報をログに記録
            logger.debug(f"Response action: {result.get('action', 'unknown')}")
            
            status_code = 400 if not result.get("success", True) else 200
            return jsonify(result), status_code
            
        except Exception as e:
            logger.error(f"Error in process route: {str(e)}")
            return _create_error_response(f"ルートエラー: {str(e)}"), 500


def _create_error_response(message: str) -> dict:
    """エラーレスポンスを生成"""
    return {
        "success": False,
        "command": "wait",
        "reasoning": message,
        "current_task": None,
        "step_id": None,
        "x": None,
        "y": None,
        "z": None
    }