"""
LLMマネージャー - 3つのLLMシステム統合
1. Task & Step Planner LLM: タスクをステップに分解
2. Step Completion Checker LLM: ステップ完了判定と次ステップ進行判断
3. Task Reconstructor LLM: エラー時のタスク再構成
"""

import json
import logging
from typing import Dict, List
from constants import get_tasks, get_dependencies, get_task_examples, get_available_commands, get_prompt_template, PROMPT_TEMPLATES

logger = logging.getLogger(__name__)

class TaskStepPlannerLLM:
    
    def __init__(self):
        self.available_commands = get_available_commands()
    
    def plan_task_steps(self, current_situation: Dict, openai_client) -> List[Dict]:
        try:
            # タスク定義を取得
            tasks = get_tasks()
            dependencies = get_dependencies()
            task_examples = get_task_examples()
            
            # 完了済みタスク履歴を取得
            from storage_manager import storage_manager
            completed_tasks = self._get_completed_tasks_history()
            
            system_prompt = """
            あなたはTask & Step Planner LLMです。現在の状況を分析し、最適なタスクを選択してステップシーケンスに分解してください。

            ## 役割
            1. **現在の状況分析**: プレイヤーの位置、所持アイテム、環境状態
            2. **完了履歴確認**: 既に完了したタスクを除外し、未完了タスクを特定
            3. **最適なタスク選択**: DAG依存関係と完了履歴に基づく実行可能タスクの選択
            4. **ステップ分解**: 選択したタスクを具体的なコマンドシーケンスに分解
            
            ## 重要な注意事項
            - 既に完了したタスクは再度実行しないでください
            - 依存関係を満たしていないタスクは選択しないでください
            - オブジェクトの位置情報には「（座標: x=数値, z=数値）」形式で絶対座標が含まれています
            - navigateコマンドでは、この絶対座標を使用してください

{get_prompt_template("available_commands")}

{get_prompt_template("step_format_example")}

            ## 出力要件
            - ステップシーケンスの配列のみを出力
            - 各ステップにはreasoningを必ず含める
            - タスク実行例の形式に厳密に従う
            """
            
            # 現在のログを整理
            logs_text = "\n".join(current_situation.get("logs", []))
            
            user_prompt = f"""
            以下の現在の状況を分析し、最適なタスクを選択してステップシーケンスに分解してください。

            ## 現在の状況
            {logs_text}

            ## 完了済みタスク履歴
            {json.dumps(completed_tasks, ensure_ascii=False, indent=2)}

            ## タスク一覧
            {json.dumps(tasks, ensure_ascii=False, indent=2)}

            ## タスク依存関係
            {json.dumps(dependencies, ensure_ascii=False, indent=2)}

            ## タスク実行例（ステップ形式の参考）
            {json.dumps(task_examples, ensure_ascii=False, indent=2)}

            **重要**: 完了済みタスク履歴を確認し、既に完了したタスクは除外してください。
            依存関係を満たし、まだ実行されていないタスクの中から最も適切なものを選択してください。
            各ステップにはreasoningを必ず含めて、そのステップで何を達成するかを明確にしてください。

            出力はステップシーケンスの配列のみとしてください。
            """
            
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content
            steps = self._extract_steps_from_response(response_text)
            
            # ステップの妥当性チェック
            validated_steps = self._validate_steps(steps)
            
            logger.info(f"Planned {len(validated_steps)} steps")
            return validated_steps
            
        except Exception as e:
            logger.error(f"Error in plan_task_steps: {str(e)}")
            error_step = PROMPT_TEMPLATES["error_fallback_step"].copy()
            error_step["reasoning"] = f"計画エラー: {str(e)}"
            return [error_step]
    
    def _get_completed_tasks_history(self) -> List[Dict]:
        """完了済みタスクの履歴を取得"""
        try:
            from storage_manager import storage_manager
            
            # タスク完了記録を取得
            task_completions = storage_manager.get_task_completions(50)  # 最大50件
            
            completed_tasks = []
            for completion in task_completions:
                if completion.get('record_type') == 'task_completion':
                    completed_task = {
                        "task_id": completion.get('completed_task_id', ''),
                        "completion_time": completion.get('timestamp', ''),
                        "completion_reasoning": completion.get('completion_reasoning', '')
                    }
                    completed_tasks.append(completed_task)
            
            logger.info(f"Retrieved {len(completed_tasks)} completed tasks")
            return completed_tasks
            
        except Exception as e:
            logger.error(f"Error getting completed tasks history: {str(e)}")
            return []
    
    def _validate_steps(self, steps: List[Dict]) -> List[Dict]:
        validated_steps = []
        valid_commands = list(self.available_commands.keys())
        
        for step in steps:
            command = step.get("command")
            if command in valid_commands:
                validated_steps.append(step)
            else:
                logger.warning(f"Invalid command in step: {command}")
                # 無効なコマンドを待機に置き換え
                error_step = PROMPT_TEMPLATES["error_fallback_step"].copy()
                error_step["reasoning"] = f"無効なコマンド ({command}) のため待機"
                validated_steps.append(error_step)
        
        return validated_steps
    
    def _extract_steps_from_response(self, response_text: str) -> List[Dict]:
        try:
            # 直接配列として解析を試行
            return json.loads(response_text)
        except json.JSONDecodeError:
            # JSONブロックを探す
            import re
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # オブジェクト形式の場合、step_sequenceを探す
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                try:
                    obj = json.loads(json_match.group(1))
                    if "step_sequence" in obj:
                        return obj["step_sequence"]
                except json.JSONDecodeError:
                    pass
            
            # デフォルト値を返す
            logger.warning(f"Failed to extract steps from response: {response_text}")
            error_step = PROMPT_TEMPLATES["error_fallback_step"].copy()
            error_step["reasoning"] = "ステップ解析失敗"
            return [error_step]


class StepCompletionCheckerLLM:
    
    def check_step_completion(self, step_info: Dict, execution_result: Dict, openai_client) -> Dict:
        try:
            system_prompt = """
            あなたはStep Completion Checker LLMです。ステップの実行結果を分析し、次の行動を決定してください。

            ## 役割
            ステップのreasoningが達成されたかを判定し、次のステップに進むか、ステップの再構築が必要かを判断する

{get_prompt_template("completion_check_criteria")}

{get_prompt_template("json_output_format")}
            """
            
            user_prompt = f"""
            以下のステップ実行結果を分析し、次の行動を判断してください。

            ## 実行されたステップ
            {json.dumps(step_info, ensure_ascii=False, indent=2)}

            ## Unity側からの実行結果
            {json.dumps(execution_result, ensure_ascii=False, indent=2)}

            ステップのreasoningで設定された目標が達成されたかを判定し、
            次のステップに進める場合は "proceed"、
            ステップの再構築が必要な場合は "rebuild" を返してください。
            """
            
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content
            result = self._extract_json_from_response(response_text)
            
            action = result.get('action', 'rebuild')
            logger.info(f"Step completion check: {action}")
            return result
            
        except Exception as e:
            logger.error(f"Error in check_step_completion: {str(e)}")
            return {
                "action": "rebuild",
                "reasoning": f"完了判定エラー: {str(e)}"
            }
    
    def _extract_json_from_response(self, response_text: str) -> Dict:
        """LLM応答からJSONを抽出"""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            logger.warning(f"Failed to extract JSON from response: {response_text}")
            return {
                "action": "rebuild",
                "reasoning": "完了判定のJSON解析失敗"
            }


class TaskReconstructorLLM:
    
    def reconstruct_task(self, error_info: Dict, current_step: Dict, openai_client) -> Dict:
        try:
            # 現在のタスクIDを取得してタスク履歴を収集
            task_execution_history = self._get_task_execution_history(current_step, error_info)
            
            system_prompt = """
            あなたはTask Reconstructor LLMです。エラーや問題が発生した際に、タスクを再構成・修正してください。

            ## 役割
            1. **エラー分析**: 発生したエラーの原因と影響を分析
            2. **履歴分析**: 同じタスクで過去に実行されたステップの時系列分析
            3. **問題解決**: エラーを回避・解決する方法を検討
            4. **タスク再構成**: 新しいアプローチでタスクを再設計
            5. **ステップ修正**: 問題を回避する新しいステップシーケンスを作成

{get_prompt_template("available_commands")}

            ## 再構成戦略
            ### エラー回避:
            - 異なる経路でのアプローチ
            - より細かいステップへの分割
            - 前提条件の再確認

            ### 代替手法:
            - 別のオブジェクトの利用
            - 手順の変更
            - 一時的な回避策

{get_prompt_template("reconstruction_output_format")}
            """
            
            user_prompt = f"""
            以下のエラー情報、失敗ステップ、およびタスク実行履歴を分析し、タスクを再構成してください。

            ## エラー情報
            {json.dumps(error_info, ensure_ascii=False, indent=2)}

            ## 失敗したステップ
            {json.dumps(current_step, ensure_ascii=False, indent=2)}

            ## タスク実行履歴（時系列順）
            {json.dumps(task_execution_history, ensure_ascii=False, indent=2)}

            **分析のポイント:**
            1. タスク実行履歴から過去に成功/失敗したパターンを特定
            2. エラーが発生した原因と繰り返しパターンを分析
            3. 既に試行されたアプローチを避けて新しい手法を検討

            エラーを回避し、同じ目標を達成するための新しいアプローチを設計してください。
            過去の履歴を踏まえ、元のreasoningを達成できる代替手段を提案してください。
            """
            
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content
            result = self._extract_json_from_response(response_text)
            
            logger.info("Task reconstruction completed")
            return result
            
        except Exception as e:
            logger.error(f"Error in reconstruct_task: {str(e)}")
            error_step = PROMPT_TEMPLATES["error_fallback_step"].copy()
            error_step["reasoning"] = f"再構成エラー: {str(e)}"
            return {
                "new_steps": [error_step]
            }
    
    def _get_task_execution_history(self, current_step: Dict, error_info: Dict) -> List[Dict]:
        """同じタスクIDの実行履歴を時系列順で取得"""
        try:
            from storage_manager import storage_manager
            
            # タスクIDを特定
            task_id = current_step.get('task_id') or error_info.get('task_id')
            if not task_id:
                # step_managerから現在のタスクIDを推測
                from step_manager import step_manager
                if step_manager.current_step_id:
                    current_step_data = step_manager.get_step(step_manager.current_step_id)
                    task_id = current_step_data.get('task_id') if current_step_data else None
            
            if not task_id:
                logger.warning("No task_id found for task execution history")
                return []
            
            # 全ログを取得してタスクIDでフィルタリング
            all_logs = storage_manager.get_log_records(100)  # 最大100件
            task_logs = []
            
            for log in all_logs:
                log_task_id = log.get('task_id')
                if log_task_id == task_id:
                    # 必要な情報のみを抽出
                    if log.get('log_type') == 'command_result_log':
                        task_log = {
                            "timestamp": log.get('timestamp', ''),
                            "step_id": log.get('step_id', ''),
                            "command": log.get('step_content', {}).get('command', ''),
                            "reasoning": log.get('step_content', {}).get('reasoning', ''),
                            "executed_command": log.get('executed_command', ''),
                            "success": log.get('success', False),
                            "result_logs": log.get('result_logs', [])
                        }
                        task_logs.append(task_log)
                    elif log.get('log_type') == 'first_log':
                        task_log = {
                            "timestamp": log.get('timestamp', ''),
                            "log_type": "task_start",
                            "initial_situation": log.get('logs', []),
                            "action": log.get('action', '')
                        }
                        task_logs.append(task_log)
            
            # 時系列順でソート
            task_logs.sort(key=lambda x: x.get('timestamp', ''))
            
            logger.info(f"Retrieved {len(task_logs)} execution history entries for task: {task_id}")
            return task_logs
            
        except Exception as e:
            logger.error(f"Error getting task execution history: {str(e)}")
            return []
    
    def _extract_json_from_response(self, response_text: str) -> Dict:
        """LLM応答からJSONを抽出"""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            logger.warning(f"Failed to extract JSON from response: {response_text}")
            error_step = PROMPT_TEMPLATES["error_fallback_step"].copy()
            error_step["reasoning"] = "JSON解析失敗"
            return {
                "new_steps": [error_step]
            }


class LLMManager:
    
    def __init__(self):
        self.planner = TaskStepPlannerLLM()
        self.checker = StepCompletionCheckerLLM()
        self.reconstructor = TaskReconstructorLLM()
    
    def plan_task(self, current_situation: Dict, openai_client) -> List[Dict]:
        return self.planner.plan_task_steps(current_situation, openai_client)
    
    def check_completion(self, step_info: Dict, execution_result: Dict, openai_client) -> Dict:
        return self.checker.check_step_completion(step_info, execution_result, openai_client)
    
    def reconstruct_task(self, error_info: Dict, current_step: Dict, openai_client) -> Dict:
        return self.reconstructor.reconstruct_task(error_info, current_step, openai_client)

# グローバルLLMマネージャーインスタンス
llm_manager = LLMManager()