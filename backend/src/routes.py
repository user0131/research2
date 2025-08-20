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
    
    # 統合APIフロー用エンドポイント
    
    @app.route('/api/process', methods=['POST', 'OPTIONS'])
    def process():
        """
        統合処理エンドポイント
        全ての処理を条件分岐アルゴリズムで自動振り分け
        """
        # CORS プリフライトリクエスト対応
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            data = request.get_json()
            
            # 入力データの基本検証
            if data is None:
                return jsonify({
                    "success": False,
                    "command": "wait",
                    "reasoning": "JSONデータが無効です",
                    "current_task": None,
                    "step_id": None,
                    "x": None,
                    "y": None,
                    "z": None
                }), 400
            
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
            return jsonify({
                "success": False,
                "command": "wait",
                "reasoning": f"ルートエラー: {str(e)}",
                "current_task": None,
                "step_id": None,
                "x": None,
                "y": None,
                "z": None
            }), 500