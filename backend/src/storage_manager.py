"""
ストレージマネージャー
ゲームログと実行コマンドの一元管理
"""

import json
import os
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class StorageManager:
    def __init__(self, storage_dir: str = "storage"):
        """
        ストレージマネージャーの初期化
        
        Args:
            storage_dir: ストレージディレクトリのパス
        """
        self.storage_dir = storage_dir
        self.game_logs_file = os.path.join(storage_dir, "game_logs.json")
        self.commands_file = os.path.join(storage_dir, "commands.json")
        
        # ストレージディレクトリを作成
        os.makedirs(storage_dir, exist_ok=True)
        
        # ファイルが存在しない場合は初期化
        self._initialize_files()
    
    def _initialize_files(self):
        """ストレージファイルを初期化"""
        if not os.path.exists(self.game_logs_file):
            with open(self.game_logs_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        
        if not os.path.exists(self.commands_file):
            with open(self.commands_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def add_log_entry(self, logs: List[str], command: str, reasoning: str, 
                     current_task: str = None, progress: str = None):
        """
        新しいログエントリを追加
        
        Args:
            logs: Unityから受信したゲームログ
            command: 実行されたコマンド
            reasoning: コマンドの理由
            current_task: 現在のタスク
            progress: 進捗状況
        """
        try:
            # ゲームログを保存
            self._save_game_logs(logs)
            
            # コマンド実行履歴を保存
            self._save_command_entry(command, reasoning, current_task, progress)
            
            logger.info(f"Added log entry - Command: {command}, Task: {current_task}")
            
        except Exception as e:
            logger.error(f"Error adding log entry: {str(e)}")
    
    def _save_game_logs(self, logs: List[str]):
        """ゲームログを保存"""
        try:
            # 既存のログを読み込み
            with open(self.game_logs_file, 'r', encoding='utf-8') as f:
                game_logs = json.load(f)
            
            # 新しいログエントリを追加
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "logs": logs
            }
            game_logs.append(log_entry)
            
            # 最新の100件のみ保持
            if len(game_logs) > 100:
                game_logs = game_logs[-100:]
            
            # ファイルに保存
            with open(self.game_logs_file, 'w', encoding='utf-8') as f:
                json.dump(game_logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving game logs: {str(e)}")
    
    def _save_command_entry(self, command: str, reasoning: str, 
                           current_task: str = None, progress: str = None):
        """コマンド実行履歴を保存"""
        try:
            # 既存のコマンド履歴を読み込み
            with open(self.commands_file, 'r', encoding='utf-8') as f:
                commands = json.load(f)
            
            # 新しいコマンドエントリを追加
            command_entry = {
                "timestamp": datetime.now().isoformat(),
                "command": command,
                "reasoning": reasoning,
                "current_task": current_task,
                "progress": progress
            }
            commands.append(command_entry)
            
            # 最新の100件のみ保持
            if len(commands) > 100:
                commands = commands[-100:]
            
            # ファイルに保存
            with open(self.commands_file, 'w', encoding='utf-8') as f:
                json.dump(commands, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving command entry: {str(e)}")
    
    def get_recent_game_logs(self, count: int = 10) -> List[Dict]:
        """最近のゲームログを取得"""
        try:
            with open(self.game_logs_file, 'r', encoding='utf-8') as f:
                game_logs = json.load(f)
            
            return game_logs[-count:] if game_logs else []
            
        except Exception as e:
            logger.error(f"Error getting recent game logs: {str(e)}")
            return []
    
    def get_recent_commands(self, count: int = 10) -> List[Dict]:
        """最近のコマンド実行履歴を取得"""
        try:
            with open(self.commands_file, 'r', encoding='utf-8') as f:
                commands = json.load(f)
            
            return commands[-count:] if commands else []
            
        except Exception as e:
            logger.error(f"Error getting recent commands: {str(e)}")
            return []
    
    def get_task_commands(self, task_id: str) -> List[Dict]:
        """特定のタスクのコマンド履歴を取得"""
        try:
            with open(self.commands_file, 'r', encoding='utf-8') as f:
                commands = json.load(f)
            
            task_commands = [
                cmd for cmd in commands 
                if cmd.get('current_task') == task_id
            ]
            return task_commands
            
        except Exception as e:
            logger.error(f"Error getting task commands: {str(e)}")
            return []
    
    def get_context_for_llm(self, current_logs: List[str] = None, 
                           recent_count: int = 5) -> Dict:
        """LLM用のコンテキストを生成"""
        try:
            recent_commands = self.get_recent_commands(recent_count)
            
            # 過去のコマンド履歴を要約
            historical_context = []
            for cmd in recent_commands:
                context_entry = {
                    'timestamp': cmd['timestamp'],
                    'command': cmd['command'],
                    'reasoning': cmd['reasoning'],
                    'current_task': cmd.get('current_task', 'unknown'),
                    'progress': cmd.get('progress', '不明')
                }
                historical_context.append(context_entry)
            
            # 現在のログと過去の文脈を結合
            context = {
                'current_logs': current_logs or [],
                'historical_context': historical_context,
                'total_commands': len(recent_commands)
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Error generating LLM context: {str(e)}")
            return {
                'current_logs': current_logs or [],
                'historical_context': [],
                'total_commands': 0
            }
    
    def get_statistics(self) -> Dict:
        """統計情報を取得"""
        try:
            # コマンド統計
            with open(self.commands_file, 'r', encoding='utf-8') as f:
                commands = json.load(f)
            
            # ゲームログ統計
            with open(self.game_logs_file, 'r', encoding='utf-8') as f:
                game_logs = json.load(f)
            
            if not commands:
                return {
                    'total_commands': 0,
                    'total_game_logs': len(game_logs),
                    'command_counts': {},
                    'task_counts': {}
                }
            
            command_counts = {}
            task_counts = {}
            
            for cmd in commands:
                # コマンドの統計
                command = cmd.get('command', 'unknown')
                command_counts[command] = command_counts.get(command, 0) + 1
                
                # タスクの統計
                task = cmd.get('current_task', 'unknown')
                task_counts[task] = task_counts.get(task, 0) + 1
            
            return {
                'total_commands': len(commands),
                'total_game_logs': len(game_logs),
                'command_counts': command_counts,
                'task_counts': task_counts,
                'first_command': commands[0]['timestamp'] if commands else None,
                'last_command': commands[-1]['timestamp'] if commands else None
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {
                'total_commands': 0,
                'total_game_logs': 0,
                'command_counts': {},
                'task_counts': {}
            }
    
    def clear_all(self):
        """すべてのデータをクリア"""
        try:
            # 空の配列で初期化
            with open(self.game_logs_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            
            with open(self.commands_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            
            logger.info("Cleared all storage data")
            
        except Exception as e:
            logger.error(f"Error clearing storage: {str(e)}")
    
    def export_data(self) -> Dict:
        """全データをエクスポート"""
        try:
            with open(self.game_logs_file, 'r', encoding='utf-8') as f:
                game_logs = json.load(f)
            
            with open(self.commands_file, 'r', encoding='utf-8') as f:
                commands = json.load(f)
            
            return {
                'game_logs': game_logs,
                'commands': commands,
                'export_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            return {
                'game_logs': [],
                'commands': [],
                'export_timestamp': datetime.now().isoformat(),
                'error': str(e)
            }

# グローバルストレージマネージャーインスタンス
storage_manager = StorageManager()