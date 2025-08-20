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
    
    @app.route('/api/process', methods=['POST'])
    def process():
        """
        統合処理エンドポイント
        全ての処理を条件分岐アルゴリズムで自動振り分け
        """
        try:
            data = request.get_json()
            openai_client = get_openai_client()
            result = command_controller.process_step(data, openai_client)
            
            status_code = 400 if not result.get("success", True) else 200
            return jsonify(result), status_code
            
        except Exception as e:
            logger.error(f"Error in process route: {str(e)}")
            return jsonify({
                "success": False,
                "error": f"エラーが発生しました: {str(e)}"
            }), 500