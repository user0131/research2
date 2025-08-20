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

logger = logging.getLogger(__name__)

class CommandController:
    """コマンド処理ロジックを管理するコントローラー"""
    
    def __init__(self):
        pass
    
    def health_check(self) -> Dict:
        """ヘルスチェック"""
        return {"status": "healthy", "message": "API is running"}
    
    # 統合APIフロー用メソッド
    
    def process_step(self, data: Dict, openai_client) -> Dict:
        """
        統合ステップ処理エンドポイント
        条件に応じてアルゴリズム的に処理を振り分け
        Unity用のCommandResponse形式で応答を返す
        """
        try:
            if not data:
                return {
                    "success": False,
                    "command": "wait",
                    "reasoning": "無効なリクエスト形式",
                    "current_task": None,
                    "step_id": None,
                    "x": None,
                    "y": None,
                    "z": None
                }
            
            # 条件分岐アルゴリズム
            action_decision = self._decide_action(data)
            
            # 決定されたアクションに基づいて処理実行
            if action_decision["action"] == "reconstruct_error":
                result = self._handle_error_reconstruction(action_decision, data, openai_client)
            elif action_decision["action"] == "plan_initial":
                result = self._handle_initial_planning(data, openai_client)
            elif action_decision["action"] == "get_next":
                result = self._handle_get_next_step()
            elif action_decision["action"] == "check_completion":
                result = self._handle_completion_check(data, openai_client)
            else:
                result = {
                    "success": False,
                    "action": "error",
                    "message": f"不明なアクション: {action_decision['action']}"
                }
            
            # Unity形式に変換して返す
            return self._convert_to_unity_format(result)
            
        except Exception as e:
            logger.error(f"Error in process_step: {str(e)}")
            return {
                "success": False,
                "command": "wait",
                "reasoning": f"エラーが発生しました: {str(e)}",
                "current_task": None,
                "step_id": None,
                "x": None,
                "y": None,
                "z": None
            }
    
    def _convert_to_unity_format(self, result: Dict) -> Dict:
        """
        バックエンドの応答をUnity用のCommandResponse形式に変換
        """
        # 基本的な応答構造
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
        
        # アクションに応じた変換
        action = result.get("action", "")
        
        if action == "step_retrieved":
            # 次ステップ取得時
            step = result.get("step", {})
            unity_response["command"] = step.get("command", "wait")
            unity_response["reasoning"] = step.get("reasoning", "")
            unity_response["step_id"] = step.get("id", "")
            unity_response["current_task"] = step.get("task_id", "")
            
            # navigateコマンドの場合、座標を設定（Y座標は省略可能）
            if step.get("command") == "navigate":
                unity_response["x"] = step.get("x")
                unity_response["y"] = step.get("y", 0)  # Y座標がない場合は0をデフォルト値とする
                unity_response["z"] = step.get("z")
                
        elif action in ["planned", "reconstructed_from_error", "task_completed_new_planned", "completion_steps_reconstructed"]:
            # タスク計画/再構成時は、すぐに次のステップを取得
            next_step = step_manager.get_next_step()
            if next_step:
                unity_response["command"] = next_step.get("command", "wait")
                unity_response["reasoning"] = next_step.get("reasoning", "")
                unity_response["step_id"] = next_step.get("id", "")
                unity_response["current_task"] = result.get("task_id", "")
                
                if next_step.get("command") == "navigate":
                    unity_response["x"] = next_step.get("x")
                    unity_response["y"] = next_step.get("y", 0)  # Y座標がない場合は0をデフォルト値とする
                    unity_response["z"] = next_step.get("z")
            else:
                # ステップがない場合はwaitコマンド
                unity_response["command"] = "wait"
                unity_response["reasoning"] = "新しいタスクを計画中"
                unity_response["current_task"] = result.get("task_id", "")
                
        elif action == "no_steps":
            # 実行可能なステップがない
            unity_response["command"] = "wait"
            unity_response["reasoning"] = "実行可能なステップがありません"
            
        else:
            # その他のアクション
            unity_response["command"] = "wait"
            unity_response["reasoning"] = result.get("message", "処理中")
            
        return unity_response
    
    def _decide_action(self, data: Dict) -> Dict:
        """
        データとシステム状態に基づいてアクションを決定
        """
        # 1. [error] / [attention] ヘッダーチェック
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
        """エラーまたは注意事項のヘッダーが含まれているかチェック"""
        logs = data.get('logs', [])
        
        for log in logs:
            log_str = str(log).lower()
            if '[error]' in log_str or '[attention]' in log_str:
                return True
        
        if data.get('error_info') or data.get('error_type'):
            return True
            
        return False
    
    def _get_error_type(self, data: Dict) -> str:
        """エラータイプを特定"""
        logs = data.get('logs', [])
        
        for log in logs:
            log_str = str(log).lower()
            if '[error]' in log_str:
                return "error"
            elif '[attention]' in log_str:
                return "attention"
        
        return "unknown_error"
    
    def _handle_error_reconstruction(self, action_decision: Dict, data: Dict, openai_client) -> Dict:
        """エラー時のタスク再構成処理（LLM3）"""
        try:
            current_step = step_manager.get_step(step_manager.current_step_id) if step_manager.current_step_id else None
            
            error_info = {
                "logs": data.get('logs', []),
                "error_type": action_decision.get("error_type", "unknown"),
                "error_details": data.get('error_info', {}),
                "timestamp": datetime.now().isoformat()
            }
            
            # LLM3でタスク再構成
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
        """初回タスク計画処理（LLM1）"""
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
        """次ステップ取得処理"""
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
        """完了判定処理（LLM2 → LLM1 または LLM3）"""
        try:
            # LLM2でタスクの終了判定
            completion_status = llm_manager.check_completion(
                {"task_summary": "全ステップ完了"}, 
                {"logs": data.get('logs', [])}, 
                openai_client
            )
            
            # LLM2の判定結果を確認
            if completion_status.get("action") == "proceed":
                # タスク完了条件を満たしている → LLM1で新タスク計画
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
                # タスク完了条件を満たしていない → LLM3で完了のためのステップ再構成
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