"""
コマンドコントローラー
APIエンドポイントの処理ロジックを管理
"""

import logging
from datetime import datetime
from typing import Dict, List
from services.llm_manager import llm_manager
from services.step_manager import step_manager
from services.storage_manager import storage_manager
from config.constants import ACTIONS, ERROR_MESSAGES

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
                return self._create_error_response(ERROR_MESSAGES["INVALID_REQUEST"])
            
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
        
        if action == ACTIONS["RECONSTRUCT_ERROR"]:
            return self._handle_error_reconstruction(action_decision, data, openai_client)
        elif action == ACTIONS["PLAN_INITIAL"]:
            return self._handle_initial_planning(data, openai_client)
        elif action == ACTIONS["GET_NEXT"]:
            return self._handle_get_next_step()
        elif action == ACTIONS["COMPLETE_STEP_AND_GET_NEXT"]:
            return self._handle_complete_step_and_get_next(data)
        elif action == ACTIONS["CHECK_TASK_COMPLETION"]:
            return self._handle_task_completion_check(data, openai_client)
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
        
        if action == ACTIONS["STEP_RETRIEVED"]:
            self._populate_step_response(unity_response, result.get("step", {}))
            
        elif action in [ACTIONS["PLANNED"], ACTIONS["RECONSTRUCTED_FROM_ERROR"], ACTIONS["TASK_COMPLETED_NEW_PLANNED"], ACTIONS["COMPLETION_STEPS_RECONSTRUCTED"], ACTIONS["STEP_COMPLETED_NEXT_RETRIEVED"]]:
            next_step = step_manager.get_next_step()
            if next_step:
                self._populate_step_response(unity_response, next_step)
                unity_response["current_task"] = result.get("task_id", "")
            else:
                unity_response["command"] = "wait"
                unity_response["reasoning"] = "新しいタスクを計画中"
                unity_response["current_task"] = result.get("task_id", "")
                
        elif action == ACTIONS["NO_STEPS"]:
            unity_response["command"] = "wait"
            unity_response["reasoning"] = "実行可能なステップがありません"
            
        else:
            unity_response["command"] = "wait"
            unity_response["reasoning"] = result.get("message", "処理中")
            
        return unity_response
    
    def _populate_step_response(self, unity_response: Dict, step: Dict):
        command = step.get("command", "wait")
        unity_response["command"] = command
        unity_response["reasoning"] = step.get("reasoning", "")
        unity_response["step_id"] = step.get("id", "")
        unity_response["current_task"] = step.get("task_id", "")
        
        # navigate(x,z)コマンドの場合、そのままUnityに送信
        # Unity側のCommandExecutorが navigate(x,z) 形式を処理する
        if command.startswith("navigate(") and command.endswith(")"):
            # navigate(x,z)形式はそのまま送信（Unity側で解析）
            pass
        elif step.get("command") == "navigate":
            # 旧形式の後方互換性のため
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
        pending_count = queue_status.get("status_counts", {}).get("pending", 0)
        executing_count = queue_status.get("status_counts", {}).get("executing", 0)
        total_steps = queue_status.get("total_steps", 0)
        
        # 2. 実行するタスクがない場合（初回）
        if total_steps == 0:
            return {
                "action": ACTIONS["PLAN_INITIAL"],
                "reason": "実行するタスクがありません（初回計画）"
            }
        
        # 3. キューにタスクが残っている場合（PENDING または EXECUTING）
        if pending_count > 0:
            return {
                "action": ACTIONS["GET_NEXT"],
                "reason": "キューに実行可能なステップがあります"
            }
        
        # 4. コマンド実行完了通知の場合（step_idがある場合）
        if data.get("step_id") and executing_count > 0:
            return {
                "action": ACTIONS["COMPLETE_STEP_AND_GET_NEXT"],
                "reason": "ステップ完了処理後、次のステップを取得"
            }
        
        # 5. キューが空になった場合（PENDING=0, EXECUTING=0）- タスク完了判定
        if pending_count == 0 and executing_count == 0 and total_steps > 0:
            return {
                "action": ACTIONS["CHECK_TASK_COMPLETION"],
                "reason": "全ステップが完了しました（タスク完了判定）"
            }
        
        # デフォルト
        return {
            "action": ACTIONS["PLAN_INITIAL"],
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
                    "action": ACTIONS["RECONSTRUCTED_FROM_ERROR"],
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
                "action": ACTIONS["PLANNED"],
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
                    "action": ACTIONS["NO_STEPS"],
                    "message": "実行可能なステップがありません",
                    "timestamp": datetime.now().isoformat()
                }
            
            logger.info(f"Retrieved next step: {next_step['id']}")
            
            return {
                "success": True,
                "action": ACTIONS["STEP_RETRIEVED"],
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
    
    
    def _get_latest_command_execution_data(self, data: Dict) -> tuple:
        """最新のコマンド実行結果をstorageから取得してLLM2用に整形"""
        try:
            # 最新のコマンド実行結果ログを取得
            latest_logs = storage_manager.get_log_records(1, "command_result_log")
            
            if latest_logs:
                latest_log = latest_logs[0]
                
                # step_info: ステップの詳細情報
                step_content = latest_log.get("step_content", {})
                step_info = {
                    "command": step_content.get("command", ""),
                    "reasoning": step_content.get("reasoning", ""),
                    "x": step_content.get("x"),
                    "z": step_content.get("z"),
                    "step_id": latest_log.get("step_id", ""),
                    "task_id": latest_log.get("task_id", "")
                }
                
                # execution_result: 実行結果の詳細
                execution_result = {
                    "executed_command": latest_log.get("executed_command", ""),
                    "result_logs": latest_log.get("result_logs", []),
                    "success": latest_log.get("success", False),
                    "timestamp": latest_log.get("timestamp", ""),
                    "current_logs": data.get('logs', [])  # 現在のリクエストログも追加
                }
                
                logger.info(f"Retrieved latest command execution data for step: {step_info.get('step_id')}")
                return step_info, execution_result
            
            else:
                # フォールバック: storageにデータがない場合
                logger.warning("No command execution logs found in storage, using fallback data")
                step_info = {"task_summary": "全ステップ完了"}
                execution_result = {"logs": data.get('logs', [])}
                return step_info, execution_result
                
        except Exception as e:
            logger.error(f"Error retrieving latest command execution data: {str(e)}")
            # エラー時のフォールバック
            step_info = {"task_summary": "全ステップ完了"}
            execution_result = {"logs": data.get('logs', [])}
            return step_info, execution_result
    
    def _handle_complete_step_and_get_next(self, data: Dict) -> Dict:
        """ステップ完了処理後、次のステップを自動的に取得"""
        try:
            step_id = data.get("step_id")
            if not step_id:
                return self._create_error_response(ERROR_MESSAGES["MISSING_STEP_ID"])
            
            # ステップを完了状態に変更
            success = step_manager.complete_step(step_id)
            if not success:
                logger.warning(f"Failed to complete step: {step_id} - may be already completed")
                # 既に完了済みの場合、キューの状態を確認
                queue_status = step_manager.get_queue_status()
                pending_count = queue_status.get("status_counts", {}).get("pending", 0)
                executing_count = queue_status.get("status_counts", {}).get("executing", 0)
                
                # 全ステップ完了の場合はLLM2による判定へ
                if pending_count == 0 and executing_count == 0:
                    logger.info("All steps completed - proceeding to task completion check")
                    # openai_clientを取得（process_stepから渡されたものを使用する必要がある）
                    # ここでは暫定的にwaitを返す
                    return {
                        "success": True,
                        "action": ACTIONS["CHECK_TASK_COMPLETION"],
                        "message": "全ステップ完了 - タスク完了判定が必要",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                # そうでなければ次のステップを取得
                return self._handle_get_next_step()
            
            logger.info(f"Step completed: {step_id}, getting next step automatically")
            
            return {
                "success": True,
                "action": ACTIONS["STEP_COMPLETED_NEXT_RETRIEVED"],
                "completed_step_id": step_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in complete step and get next: {str(e)}")
            return self._create_error_response(f"{ERROR_MESSAGES['STEP_COMPLETION_ERROR']}: {str(e)}")
    
    def _handle_task_completion_check(self, data: Dict, openai_client) -> Dict:
        """タスク全体の完了判定（LLM2をタスク完了時のみ呼び出し）"""
        try:
            current_task_id = self._get_current_task_id()
            task_execution_history = self._get_task_execution_history_for_completion(current_task_id)
            
            completion_status = self._check_task_completion_with_llm(current_task_id, task_execution_history, data, openai_client)
            
            if completion_status.get("action") == "proceed":
                return self._handle_task_completed(current_task_id, completion_status, data, openai_client)
            else:
                return self._handle_task_incomplete(current_task_id, completion_status, task_execution_history, data, openai_client)
                    
        except Exception as e:
            logger.error(f"Error in task completion check: {str(e)}")
            return self._create_error_response(f"{ERROR_MESSAGES['TASK_COMPLETION_CHECK_ERROR']}: {str(e)}")
    
    def _check_task_completion_with_llm(self, task_id: str, history: List[Dict], data: Dict, openai_client) -> Dict:
        """LLM2でタスク全体の完了判定"""
        return llm_manager.check_completion(
            {"task_id": task_id, "task_summary": "全ステップ完了"},
            {"task_execution_history": history, "current_logs": data.get('logs', [])},
            openai_client
        )
    
    def _handle_task_completed(self, task_id: str, completion_status: Dict, data: Dict, openai_client) -> Dict:
        """タスク完了時の処理"""
        logger.info("Task completion criteria satisfied, planning new task")
        new_planning_result = self._handle_initial_planning(data, openai_client)
        
        return {
            "success": True,
            "action": ACTIONS["TASK_COMPLETED_NEW_PLANNED"],
            "completed_task_id": task_id,
            "completion_reasoning": completion_status.get("reasoning", ""),
            "new_planning": new_planning_result,
            "timestamp": datetime.now().isoformat()
        }
    
    def _handle_task_incomplete(self, task_id: str, completion_status: Dict, history: List[Dict], data: Dict, openai_client) -> Dict:
        """タスク未完了時の再構成処理"""
        logger.info("Task completion criteria not satisfied, reconstructing steps for completion")
        
        completion_info = {
            "logs": data.get('logs', []),
            "completion_status": completion_status,
            "incomplete_reason": completion_status.get("reasoning", ""),
            "task_execution_history": history,
            "timestamp": datetime.now().isoformat()
        }
        
        reconstruction_result = llm_manager.reconstruct_task(
            completion_info,
            {"task_id": task_id, "task_summary": "タスク完了のための追加ステップが必要"},
            openai_client
        )
        
        if reconstruction_result.get("new_steps"):
            step_manager.clear_all_steps()
            new_task_id = f"completion_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            step_ids = step_manager.add_steps(new_task_id, reconstruction_result["new_steps"])
            
            logger.info(f"Completion steps reconstructed: {new_task_id}")
            
            return {
                "success": True,
                "action": ACTIONS["COMPLETION_STEPS_RECONSTRUCTED"],
                "completion_reasoning": completion_status.get("reasoning", ""),
                "task_id": new_task_id,
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
    
    def _get_current_task_id(self) -> str:
        """現在のタスクIDを取得"""
        try:
            # step_managerから現在実行中または最新のタスクIDを取得
            if step_manager.current_step_id:
                current_step = step_manager.get_step(step_manager.current_step_id)
                if current_step:
                    return current_step.get('task_id', '')
            
            # current_step_idがない場合、最新のCOMPLETEDステップからタスクIDを取得
            queue_status = step_manager.get_queue_status()
            if queue_status.get("total_steps", 0) > 0:
                # 最新のステップのタスクIDを取得
                latest_step = step_manager.steps[-1] if step_manager.steps else None
                if latest_step:
                    return latest_step.get('task_id', '')
            
            return ""
        except Exception as e:
            logger.error(f"{ERROR_MESSAGES['CURRENT_TASK_ID_ERROR']}: {str(e)}")
            return ""
    
    def _get_task_execution_history_for_completion(self, task_id: str) -> List[Dict]:
        """タスク完了判定用の実行履歴を取得"""
        try:
            if not task_id:
                return []
            
            # storageから同じタスクIDの実行ログを取得するためのベース処理
            
            # storageから同じタスクIDの実行ログを取得
            all_logs = storage_manager.get_log_records(100)
            task_execution_logs = []
            
            for log in all_logs:
                if log.get('task_id') == task_id and log.get('log_type') == 'command_result_log':
                    execution_log = {
                        "timestamp": log.get('timestamp', ''),
                        "step_id": log.get('step_id', ''),
                        "command": log.get('step_content', {}).get('command', ''),
                        "reasoning": log.get('step_content', {}).get('reasoning', ''),
                        "executed_command": log.get('executed_command', ''),
                        "success": log.get('success', False),
                        "result_logs": log.get('result_logs', [])
                    }
                    task_execution_logs.append(execution_log)
            
            # 時系列順でソート
            task_execution_logs.sort(key=lambda x: x.get('timestamp', ''))
            
            logger.info(f"Retrieved {len(task_execution_logs)} execution logs for task completion check: {task_id}")
            return task_execution_logs
            
        except Exception as e:
            logger.error(f"{ERROR_MESSAGES['TASK_EXECUTION_HISTORY_ERROR']}: {str(e)}")
            return []


# グローバルコントローラーインスタンス
command_controller = CommandController()