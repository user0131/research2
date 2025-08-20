"""
コマンドコントローラー
APIエンドポイントの処理ロジックを管理
"""

import logging
from datetime import datetime
from typing import Dict
from llm_manager import llm_manager
from step_manager import step_manager
from storage_manager import storage_manager

logger = logging.getLogger(__name__)


class CommandController:
    
    def __init__(self):
        pass
    
    # === パブリックメソッド ===
    
    def health_check(self) -> Dict:
        return {"status": "healthy", "message": "API is running"}
    
    def process_step(self, data: Dict, openai_client) -> Dict:
        try:
            if not data:
                return self._create_error_response("無効なリクエスト形式")
            
            # 条件分岐アルゴリズム
            action_decision = self._decide_action(data)
            
            # 決定されたアクションに基づいて処理実行
            result = self._execute_action(action_decision, data, openai_client)
            
            # Unity形式に変換して返す
            unity_response = self._convert_to_unity_format(result)
            
            # ログの記録保存
            storage_manager.process_and_save_logs(data, unity_response, result)
            
            return unity_response
            
        except Exception as e:
            logger.error(f"Error in process_step: {str(e)}")
            return self._create_error_response(f"エラーが発生しました: {str(e)}")
    
    # === プライベートメソッド - ユーティリティ ===
    
    def _create_error_response(self, message: str) -> Dict:
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
    
    def _execute_action(self, action_decision: Dict, data: Dict, openai_client) -> Dict:
        action = action_decision["action"]
        
        if action == "reconstruct_error":
            return self._handle_error_reconstruction(action_decision, data, openai_client)
        elif action == "plan_initial":
            return self._handle_initial_planning(data, openai_client)
        elif action == "get_next":
            return self._handle_get_next_step()
        elif action == "check_completion":
            return self._handle_completion_check(data, openai_client)
        else:
            return {
                "success": False,
                "action": "error",
                "message": f"不明なアクション: {action}"
            }
    
    def _convert_to_unity_format(self, result: Dict) -> Dict:
        unity_response = {
            "success": result.get("success", False),
            "command": None,
            "reasoning": None,
            "current_task": None,
            "step_id": None,
            "x": None,
            "y": None,
            "z": None
        }
        
        action = result.get("action", "")
        
        if action == "step_retrieved":
            self._populate_step_response(unity_response, result.get("step", {}))
            
        elif action in ["planned", "reconstructed_from_error", "task_completed_new_planned", "completion_steps_reconstructed"]:
            next_step = step_manager.get_next_step()
            if next_step:
                self._populate_step_response(unity_response, next_step)
                unity_response["current_task"] = result.get("task_id", "")
            else:
                unity_response["command"] = "wait"
                unity_response["reasoning"] = "新しいタスクを計画中"
                unity_response["current_task"] = result.get("task_id", "")
                
        elif action == "no_steps":
            unity_response["command"] = "wait"
            unity_response["reasoning"] = "実行可能なステップがありません"
            
        else:
            unity_response["command"] = "wait"
            unity_response["reasoning"] = result.get("message", "処理中")
            
        return unity_response
    
    def _populate_step_response(self, unity_response: Dict, step: Dict):
        unity_response["command"] = step.get("command", "wait")
        unity_response["reasoning"] = step.get("reasoning", "")
        unity_response["step_id"] = step.get("id", "")
        unity_response["current_task"] = step.get("task_id", "")
        
        # navigateコマンドの場合、座標を設定
        if step.get("command") == "navigate":
            unity_response["x"] = step.get("x")
            unity_response["y"] = step.get("y", 0)  # Y座標がない場合は0をデフォルト値
            unity_response["z"] = step.get("z")
    
    # === プライベートメソッド - アクション決定 ===
    
    def _decide_action(self, data: Dict) -> Dict:
        # 1. エラー/注意事項チェック
        if self._has_error_or_attention_header(data):
            return {
                "action": "reconstruct_error",
                "reason": "エラーまたは注意事項が検出されました",
                "error_type": self._get_error_type(data)
            }
        
        # キューの状態を取得
        queue_status = step_manager.get_queue_status()
        
        # 2. 実行するタスクがない場合（初回）
        if not queue_status.get("has_pending_steps", False) and queue_status.get("total_steps", 0) == 0:
            return {
                "action": "plan_initial",
                "reason": "実行するタスクがありません（初回計画）"
            }
        
        # 3. キューにタスクが残っている場合
        if queue_status.get("has_pending_steps", False):
            return {
                "action": "get_next",
                "reason": "キューに実行可能なステップがあります"
            }
        
        # 4. キューを全て消化した場合（終了判定）
        if queue_status.get("total_steps", 0) > 0 and not queue_status.get("has_pending_steps", False):
            return {
                "action": "check_completion",
                "reason": "全ステップが完了しました（終了判定とタスク完了確認）"
            }
        
        # デフォルト
        return {
            "action": "plan_initial",
            "reason": "想定外の状況のため初回計画にフォールバック"
        }
    
    def _has_error_or_attention_header(self, data: Dict) -> bool:
        logs = data.get('logs', [])
        
        for log in logs:
            log_str = str(log).lower()
            if '[error]' in log_str or '[attention]' in log_str:
                return True
        
        return bool(data.get('error_info') or data.get('error_type'))
    
    def _get_error_type(self, data: Dict) -> str:
        logs = data.get('logs', [])
        
        for log in logs:
            log_str = str(log).lower()
            if '[error]' in log_str:
                return "error"
            elif '[attention]' in log_str:
                return "attention"
        
        return "unknown_error"
    
    # === プライベートメソッド - アクションハンドラー ===
    
    def _handle_error_reconstruction(self, action_decision: Dict, data: Dict, openai_client) -> Dict:
        try:
            current_step = step_manager.get_step(step_manager.current_step_id) if step_manager.current_step_id else None
            
            error_info = {
                "logs": data.get('logs', []),
                "error_type": action_decision.get("error_type", "unknown"),
                "error_details": data.get('error_info', {}),
                "timestamp": datetime.now().isoformat()
            }
            
            reconstruction_result = llm_manager.reconstruct_task(error_info, current_step or {}, openai_client)
            
            if reconstruction_result.get("new_steps"):
                step_manager.clear_all_steps()
                task_id = f"reconstructed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                step_ids = step_manager.add_steps(task_id, reconstruction_result["new_steps"])
                
                logger.info(f"Task reconstructed due to error: {task_id}")
                
                return {
                    "success": True,
                    "action": "reconstructed_from_error",
                    "task_id": task_id,
                    "new_steps_count": len(reconstruction_result["new_steps"]),
                    "step_ids": step_ids,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "action": "reconstruction_failed",
                    "error": "エラー再構成で新しいステップが生成されませんでした",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error in error reconstruction: {str(e)}")
            return {
                "success": False,
                "action": "reconstruction_error",
                "error": f"エラー再構成中にエラーが発生: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def _handle_initial_planning(self, data: Dict, openai_client) -> Dict:
        try:
            logs = data.get('logs', [])
            
            if not logs:
                return {"success": False, "error": "ログが提供されていません"}
            
            current_situation = {"logs": logs}
            steps = llm_manager.plan_task(current_situation, openai_client)
            
            task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            step_ids = step_manager.add_steps(task_id, steps)
            
            logger.info(f"Initial task planned: {task_id}")
            
            return {
                "success": True,
                "action": "planned",
                "task_id": task_id,
                "steps_planned": len(steps),
                "step_ids": step_ids,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in initial planning: {str(e)}")
            return {
                "success": False,
                "action": "planning_error",
                "error": f"初回計画中にエラーが発生: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def _handle_get_next_step(self) -> Dict:
        try:
            next_step = step_manager.get_next_step()
            
            if next_step is None:
                return {
                    "success": True,
                    "action": "no_steps",
                    "message": "実行可能なステップがありません",
                    "timestamp": datetime.now().isoformat()
                }
            
            logger.info(f"Retrieved next step: {next_step['id']}")
            
            return {
                "success": True,
                "action": "step_retrieved",
                "step": next_step,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting next step: {str(e)}")
            return {
                "success": False,
                "action": "get_step_error",
                "error": f"ステップ取得中にエラーが発生: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def _handle_completion_check(self, data: Dict, openai_client) -> Dict:
        try:
            completion_status = llm_manager.check_completion(
                {"task_summary": "全ステップ完了"}, 
                {"logs": data.get('logs', [])}, 
                openai_client
            )
            
            if completion_status.get("action") == "proceed":
                # タスク完了条件を満たしている → 新タスク計画
                logger.info("Task completion criteria satisfied, planning new task")
                
                new_planning_result = self._handle_initial_planning(data, openai_client)
                
                return {
                    "success": True,
                    "action": "task_completed_new_planned",
                    "completion_reasoning": completion_status.get("reasoning", ""),
                    "new_planning": new_planning_result,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # タスク完了条件を満たしていない → 完了のためのステップ再構成
                logger.info("Task completion criteria not satisfied, reconstructing steps for completion")
                
                completion_info = {
                    "logs": data.get('logs', []),
                    "completion_status": completion_status,
                    "incomplete_reason": completion_status.get("reasoning", ""),
                    "timestamp": datetime.now().isoformat()
                }
                
                reconstruction_result = llm_manager.reconstruct_task(
                    completion_info, 
                    {"task_summary": "タスク完了のための追加ステップが必要"}, 
                    openai_client
                )
                
                if reconstruction_result.get("new_steps"):
                    step_manager.clear_all_steps()
                    task_id = f"completion_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    step_ids = step_manager.add_steps(task_id, reconstruction_result["new_steps"])
                    
                    logger.info(f"Completion steps reconstructed: {task_id}")
                    
                    return {
                        "success": True,
                        "action": "completion_steps_reconstructed", 
                        "completion_reasoning": completion_status.get("reasoning", ""),
                        "task_id": task_id,
                        "new_steps_count": len(reconstruction_result["new_steps"]),
                        "step_ids": step_ids,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "success": False,
                        "action": "completion_reconstruction_failed",
                        "error": "タスク完了のためのステップ再構成に失敗しました",
                        "completion_reasoning": completion_status.get("reasoning", ""),
                        "timestamp": datetime.now().isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"Error in completion check: {str(e)}")
            return {
                "success": False,
                "action": "completion_check_error",
                "error": f"完了判定中にエラーが発生: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }


# グローバルコントローラーインスタンス
command_controller = CommandController()