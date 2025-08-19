"""
コマンドコントローラー
APIエンドポイントの処理ロジックを管理
"""

import logging
from datetime import datetime
from typing import Dict, List
from llm_manager import llm_manager
from step_manager import step_manager
from storage_manager import storage_manager
from task_definitions import (
    get_goal, get_tasks, get_dependencies, 
    get_task_description, get_task_dependencies,
    get_task_examples, get_task_example
)

logger = logging.getLogger(__name__)

class CommandController:
    """コマンド処理ロジックを管理するコントローラー"""
    
    def __init__(self):
        pass
    
    def health_check(self) -> Dict:
        """ヘルスチェック"""
        return {"status": "healthy", "message": "API is running"}
    
    def process_logs(self, data: Dict, openai_client) -> Dict:
        """ログを処理してコマンドを決定（旧システム用）"""
        try:
            if not data:
                return {"success": False, "command": "wait", "reasoning": "無効なリクエスト形式"}
            
            logs = data.get('logs', [])
            
            if not logs:
                return {"success": False, "command": "wait", "reasoning": "ログが提供されていません"}
            
            # 過去のログコンテキストを取得
            log_context = storage_manager.get_context_for_llm(logs)
            
            # 旧システムでの処理（後で削除予定）
            logger.warning("Using deprecated process_logs endpoint")
            
            # ログエントリを保存
            storage_manager.add_log_entry(
                logs=logs,
                command="wait",
                reasoning="旧システムでの処理",
                current_task="unknown",
                progress="不明"
            )
            
            return {
                "success": True,
                "command": "wait",
                "reasoning": "旧システムは非推奨です。新しいAPIフローを使用してください。",
                "current_task": "unknown",
                "progress": "不明"
            }
            
        except Exception as e:
            logger.error(f"Error processing logs: {str(e)}")
            return {
                "success": False,
                "command": "wait",
                "reasoning": f"エラーが発生しました: {str(e)}"
            }
    
    def get_logs(self, page: int = 1, per_page: int = 10) -> Dict:
        """ログ履歴を取得"""
        try:
            logs = storage_manager.get_recent_commands(count=per_page)
            
            return {
                "logs": logs,
                "page": page,
                "per_page": per_page,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting logs: {str(e)}")
            return {"error": str(e)}
    
    def get_log_stats(self) -> Dict:
        """ログ統計を取得"""
        try:
            stats = storage_manager.get_statistics()
            return {
                "statistics": stats,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting log stats: {str(e)}")
            return {"error": str(e)}
    
    def get_task_status(self) -> Dict:
        """タスクの状況を取得"""
        try:
            dependencies = get_dependencies()
            tasks = get_tasks()
            goal = get_goal()
            
            return {
                "goal": goal,
                "tasks": tasks,
                "dependencies": dependencies,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting task status: {str(e)}")
            return {"error": str(e)}
    
    def clear_logs(self) -> Dict:
        """ログをクリア"""
        try:
            storage_manager.clear_all()
            return {
                "message": "ログがクリアされました",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error clearing logs: {str(e)}")
            return {"error": str(e)}
    
    def export_logs(self) -> Dict:
        """ログをエクスポート"""
        try:
            export_data = storage_manager.export_data()
            return {
                "export_data": export_data,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error exporting logs: {str(e)}")
            return {"error": str(e)}
    
    def get_log_context(self) -> Dict:
        """ログコンテキストを取得"""
        try:
            context = storage_manager.get_context_for_llm()
            return {
                "context": context,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting log context: {str(e)}")
            return {"error": str(e)}
    
    # 新しいAPIフロー用メソッド
    
    def plan_task(self, data: Dict, openai_client) -> Dict:
        """タスク計画: LLMでタスクをステップに分解してキューに追加"""
        try:
            if not data:
                return {"success": False, "error": "無効なリクエスト形式"}
            
            logs = data.get('logs', [])
            
            if not logs:
                return {"success": False, "error": "ログが提供されていません"}
            
            # 現在の状況を構築
            current_situation = {"logs": logs}
            
            # LLM1でタスクをステップに分解
            steps = llm_manager.plan_task(current_situation, openai_client)
            
            # ステップをキューに追加
            task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            step_ids = step_manager.add_steps(task_id, steps)
            
            # ログに記録
            logger.info(f"Planned task {task_id} with {len(steps)} steps")
            
            return {
                "success": True,
                "task_id": task_id,
                "steps_planned": len(steps),
                "step_ids": step_ids,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in plan_task: {str(e)}")
            return {
                "success": False,
                "error": f"エラーが発生しました: {str(e)}"
            }
    
    def get_next_step(self) -> Dict:
        """次のステップ取得"""
        try:
            # キューから次のステップを取得
            next_step = step_manager.get_next_step()
            
            if next_step is None:
                return {
                    "has_step": False,
                    "message": "実行可能なステップがありません",
                    "queue_status": step_manager.get_queue_status(),
                    "timestamp": datetime.now().isoformat()
                }
            
            logger.info(f"Retrieved next step: {next_step['id']}")
            
            return {
                "has_step": True,
                "step": next_step,
                "queue_status": step_manager.get_queue_status(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in get_next_step: {str(e)}")
            return {
                "has_step": False,
                "error": f"エラーが発生しました: {str(e)}"
            }
    
    def complete_step(self, step_id: str, data: Dict, openai_client) -> Dict:
        """ステップ完了通知とLLM2による判定"""
        try:
            if not data:
                return {"success": False, "error": "無効なリクエスト形式"}
            
            # ステップ情報を取得
            step_info = step_manager.get_step(step_id)
            
            if step_info is None:
                return {"success": False, "error": "ステップが見つかりません"}
            
            # Unity側からの実行結果
            execution_result = data.get('execution_result', {})
            
            # LLM2でステップ完了を判定
            completion_check = llm_manager.check_completion(step_info, execution_result, openai_client)
            
            action = completion_check.get('action', 'rebuild')
            
            if action == 'proceed':
                # ステップを完了状態にマーク
                step_manager.complete_step(step_id)
                logger.info(f"Step {step_id} completed successfully")
                
                return {
                    "success": True,
                    "action": "proceed",
                    "reasoning": completion_check.get('reasoning', ''),
                    "next_step_available": step_manager.get_queue_status()["has_pending_steps"],
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # ステップを失敗状態にマーク
                step_manager.fail_step(step_id, completion_check.get('reasoning', 'ステップ再構築が必要'))
                logger.info(f"Step {step_id} requires rebuild")
                
                return {
                    "success": True,
                    "action": "rebuild",
                    "reasoning": completion_check.get('reasoning', ''),
                    "rebuild_required": True,
                    "timestamp": datetime.now().isoformat()
                }
            
        except Exception as e:
            logger.error(f"Error in complete_step: {str(e)}")
            return {
                "success": False,
                "error": f"エラーが発生しました: {str(e)}"
            }
    
    def handle_event(self, data: Dict, openai_client) -> Dict:
        """エラー時やイベント時の処理"""
        try:
            if not data:
                return {"success": False, "error": "無効なリクエスト形式"}
            
            step_id = data.get('step_id')
            error_info = data.get('error_info', {})
            
            if step_id:
                # 特定のステップに関するイベント
                step_info = step_manager.get_step(step_id)
                
                if step_info is None:
                    return {"success": False, "error": "ステップが見つかりません"}
                
                # LLM2でエラー状況を判定
                completion_check = llm_manager.check_completion(step_info, error_info, openai_client)
                
                action = completion_check.get('action', 'rebuild')
                
                if action == 'rebuild':
                    # ステップを失敗状態にマーク
                    step_manager.fail_step(step_id, completion_check.get('reasoning', 'エラーによるステップ再構築'))
                    
                    return {
                        "success": True,
                        "action": "rebuild",
                        "reasoning": completion_check.get('reasoning', ''),
                        "requires_replanning": True,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "success": True,
                        "action": action,
                        "reasoning": completion_check.get('reasoning', ''),
                        "timestamp": datetime.now().isoformat()
                    }
            else:
                # 一般的なエラーイベント
                logger.error(f"General error event: {error_info}")
                
                return {
                    "success": True,
                    "action": "rebuild",
                    "reasoning": "一般的なエラーが発生したため再計画が必要",
                    "requires_replanning": True,
                    "timestamp": datetime.now().isoformat()
                }
            
        except Exception as e:
            logger.error(f"Error in handle_event: {str(e)}")
            return {
                "success": False,
                "error": f"エラーが発生しました: {str(e)}"
            }

# グローバルコントローラーインスタンス
command_controller = CommandController()