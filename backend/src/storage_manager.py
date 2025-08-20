"""
ストレージマネージャー
ゲームログと実行コマンドの一元管理
"""

import json
import os
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

class StorageManager:
    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = storage_dir
        self.log_file = os.path.join(storage_dir, "log_file.json")
        
        # ストレージディレクトリを作成
        os.makedirs(storage_dir, exist_ok=True)
        
        # ファイルが存在しない場合は初期化
        self._initialize_files()
    
    def _initialize_files(self):
        """ストレージファイルを初期化"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    
    def clear_all(self):
        """すべてのデータをクリア"""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            
            logger.info("Cleared all log data")
            
        except Exception as e:
            logger.error(f"Error clearing log data: {str(e)}")
    
    
    def save_log_record(self, log_record: Dict):
        """統合ログに記録を保存"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
            
            records.append(log_record)
            
            # 最新の100件のみ保持
            if len(records) > 100:
                records = records[-100:]
            
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            
            record_type = log_record.get('log_type') or log_record.get('record_type', 'unknown')
            logger.info(f"Saved log: {record_type}")
                
        except Exception as e:
            logger.error(f"Error saving log record: {str(e)}")
    
    def save_task_completion(self, completion_record: Dict):
        """タスク完了記録を統合ログに保存"""
        self.save_log_record(completion_record)
    
    def get_log_records(self, count: int = 20, log_type: str = None) -> List[Dict]:
        """統合ログから記録を取得"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
            
            # ログタイプでフィルタリング
            if log_type:
                filtered_records = [
                    r for r in records 
                    if r.get('log_type') == log_type or r.get('record_type') == log_type
                ]
                return filtered_records[-count:] if filtered_records else []
            
            return records[-count:] if records else []
            
        except Exception as e:
            logger.error(f"Error getting log records: {str(e)}")
            return []
    
    def get_task_completions(self, count: int = 10) -> List[Dict]:
        """タスク完了記録を取得"""
        return self.get_log_records(count, "task_completion")
    
    def process_and_save_logs(self, input_data: Dict, unity_response: Dict, processing_result: Dict):
        """
        ログを処理して適切な形式で保存
        初回ログか、コマンド実行後のログかを判定して保存
        """
        try:
            logs = input_data.get('logs', [])
            if not logs:
                return
            
            # 現在のタスクとステップ情報を取得
            current_task = unity_response.get('current_task', '')
            step_id = unity_response.get('step_id', '')
            executed_command = unity_response.get('command', '')
            
            # アクションによってログの種類を判定
            action = processing_result.get('action', '')
            
            if action in ['plan_initial', 'reconstruct_error'] and not step_id:
                # 初回ログ（何もコマンドを実行する前）
                log_record = {
                    "log_type": "first_log",
                    "timestamp": datetime.now().isoformat(),
                    "logs": logs,
                    "task_id": current_task,
                    "action": action
                }
                self.save_log_record(log_record)
                logger.info(f"Saved first log record for action: {action}")
                
            elif step_id and executed_command:
                # コマンド実行後のログ
                from step_manager import step_manager
                step_info = step_manager.get_step(step_id) if step_id else {}
                
                log_record = {
                    "log_type": "command_result_log", 
                    "timestamp": datetime.now().isoformat(),
                    "task_id": current_task,
                    "step_id": step_id,
                    "step_content": {
                        "command": step_info.get('command', executed_command),
                        "reasoning": step_info.get('reasoning', ''),
                        "x": step_info.get('x'),
                        "y": step_info.get('y'),
                        "z": step_info.get('z')
                    },
                    "executed_command": executed_command,
                    "result_logs": logs,
                    "success": unity_response.get('success', False)
                }
                self.save_log_record(log_record)
                logger.info(f"Saved command result log for step: {step_id}")
            
            # タスク完了時の記録
            if action in ['task_completed_new_planned']:
                completion_record = {
                    "record_type": "task_completion",
                    "timestamp": datetime.now().isoformat(),
                    "completed_task_id": current_task,
                    "completion_reasoning": processing_result.get('completion_reasoning', ''),
                    "new_task_started": processing_result.get('new_planning', {}).get('task_id', '')
                }
                self.save_task_completion(completion_record)
                logger.info(f"Saved task completion record for task: {current_task}")
                
        except Exception as e:
            logger.error(f"Error processing and saving logs: {str(e)}")

# グローバルストレージマネージャーインスタンス
storage_manager = StorageManager()