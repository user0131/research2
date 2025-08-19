"""
ログ管理モジュール
ゲームログの保存・取得・分析機能を提供
"""

import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class LogManager:
    """ゲームログの保存・管理クラス"""
    
    def __init__(self, log_file_path: str = "game_logs.json"):
        self.log_file_path = log_file_path
        self.session_logs = []  # 現在のセッションのログ
        self.load_logs()
    
    def load_logs(self):
        """保存されたログを読み込み"""
        try:
            if os.path.exists(self.log_file_path):
                with open(self.log_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.session_logs = data.get('sessions', [])
                    logger.info(f"Loaded {len(self.session_logs)} log sessions")
            else:
                self.session_logs = []
                logger.info("No existing log file found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading logs: {str(e)}")
            self.session_logs = []
    
    def save_logs(self):
        """ログをファイルに保存"""
        try:
            data = {
                'sessions': self.session_logs,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(self.session_logs)} log sessions")
        except Exception as e:
            logger.error(f"Error saving logs: {str(e)}")
    
    def add_log_entry(self, logs: List[str], command: str, reasoning: str, 
                     current_task: str = None, progress: str = None):
        """新しいログエントリを追加"""
        try:
            entry = {
                'timestamp': datetime.now().isoformat(),
                'logs': logs,
                'command': command,
                'reasoning': reasoning,
                'current_task': current_task,
                'progress': progress
            }
            
            self.session_logs.append(entry)
            
            # ログが多くなりすぎないように制限（最新100件まで）
            if len(self.session_logs) > 100:
                self.session_logs = self.session_logs[-100:]
            
            # 自動保存
            self.save_logs()
            
            logger.info(f"Added new log entry. Total entries: {len(self.session_logs)}")
            
        except Exception as e:
            logger.error(f"Error adding log entry: {str(e)}")
    
    def get_recent_logs(self, count: int = 10) -> List[Dict]:
        """最近のログを取得"""
        try:
            return self.session_logs[-count:] if self.session_logs else []
        except Exception as e:
            logger.error(f"Error getting recent logs: {str(e)}")
            return []
    
    def get_task_history(self, task_id: str) -> List[Dict]:
        """特定のタスクの履歴を取得"""
        try:
            task_logs = []
            for entry in self.session_logs:
                if entry.get('current_task') == task_id:
                    task_logs.append(entry)
            return task_logs
        except Exception as e:
            logger.error(f"Error getting task history: {str(e)}")
            return []
    
    def get_context_for_llm(self, current_logs: List[str], 
                           recent_count: int = 5) -> Dict:
        """LLM用のコンテキストを生成"""
        try:
            recent_logs = self.get_recent_logs(recent_count)
            
            # 過去のログを要約
            historical_context = []
            for entry in recent_logs:
                context_entry = {
                    'timestamp': entry['timestamp'],
                    'command': entry['command'],
                    'reasoning': entry['reasoning'],
                    'current_task': entry.get('current_task', 'unknown'),
                    'progress': entry.get('progress', '不明')
                }
                historical_context.append(context_entry)
            
            # 現在のログと過去の文脈を結合
            context = {
                'current_logs': current_logs,
                'historical_context': historical_context,
                'total_entries': len(self.session_logs)
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Error generating LLM context: {str(e)}")
            return {
                'current_logs': current_logs,
                'historical_context': [],
                'total_entries': 0
            }
    
    def get_task_progress_summary(self) -> Dict:
        """タスクの進捗状況のサマリーを取得"""
        try:
            task_progress = {
                'step1': {'attempts': 0, 'completed': False, 'last_action': None},
                'step2': {'attempts': 0, 'completed': False, 'last_action': None},
                'step3': {'attempts': 0, 'completed': False, 'last_action': None},
                'step4': {'attempts': 0, 'completed': False, 'last_action': None}
            }
            
            for entry in self.session_logs:
                task_id = entry.get('current_task')
                if task_id and task_id in task_progress:
                    task_progress[task_id]['attempts'] += 1
                    task_progress[task_id]['last_action'] = {
                        'command': entry['command'],
                        'timestamp': entry['timestamp'],
                        'reasoning': entry['reasoning']
                    }
                    
                    # 完了判定（簡単な例）
                    if 'completed' in entry.get('progress', '').lower():
                        task_progress[task_id]['completed'] = True
            
            return task_progress
            
        except Exception as e:
            logger.error(f"Error getting task progress summary: {str(e)}")
            return {}
    
    def clear_logs(self):
        """ログをクリア"""
        try:
            self.session_logs = []
            self.save_logs()
            logger.info("Cleared all logs")
        except Exception as e:
            logger.error(f"Error clearing logs: {str(e)}")
    
    def get_statistics(self) -> Dict:
        """ログの統計情報を取得"""
        try:
            if not self.session_logs:
                return {'total_entries': 0, 'commands': {}, 'tasks': {}}
            
            command_counts = {}
            task_counts = {}
            
            for entry in self.session_logs:
                # コマンドの統計
                command = entry.get('command', 'unknown')
                command_counts[command] = command_counts.get(command, 0) + 1
                
                # タスクの統計
                task = entry.get('current_task', 'unknown')
                task_counts[task] = task_counts.get(task, 0) + 1
            
            return {
                'total_entries': len(self.session_logs),
                'commands': command_counts,
                'tasks': task_counts,
                'first_entry': self.session_logs[0]['timestamp'],
                'last_entry': self.session_logs[-1]['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {'total_entries': 0, 'commands': {}, 'tasks': {}} 