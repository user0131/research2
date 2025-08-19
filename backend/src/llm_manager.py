"""
LLMマネージャー - 2つのLLMシステム統合
1. Task & Step Planner LLM: タスクをステップに分解
2. Step Completion Checker LLM: ステップ完了判定と次ステップ進行判断
"""

import json
import logging
from typing import Dict, List
from task_definitions import get_tasks, get_dependencies, get_task_examples, get_available_commands

logger = logging.getLogger(__name__)

class TaskStepPlannerLLM:
    """Task & Step Planner LLM - タスクをステップシーケンスに分解"""
    
    def __init__(self):
        self.available_commands = get_available_commands()
    
    def plan_task_steps(self, current_situation: Dict, openai_client) -> List[Dict]:
        """
        現在の状況からタスクとステップを計画
        
        Args:
            current_situation: 現在の状況（ログ、位置等）
            openai_client: OpenAIクライアント
            
        Returns:
            ステップシーケンス
        """
        try:
            # タスク定義を取得
            tasks = get_tasks()
            dependencies = get_dependencies()
            task_examples = get_task_examples()
            
            system_prompt = """
            あなたはTask & Step Planner LLMです。現在の状況を分析し、最適なタスクを選択してステップシーケンスに分解してください。

            ## 役割
            1. **現在の状況分析**: プレイヤーの位置、所持アイテム、環境状態
            2. **最適なタスク選択**: DAG依存関係に基づく実行可能タスクの選択
            3. **ステップ分解**: 選択したタスクを具体的なコマンドシーケンスに分解

            ## 利用可能なコマンド
            - "navigate": 指定座標への移動 (parameters: x, y, z)
            - "pickup": アイテムの拾い上げ/設置
            - "interact": オブジェクトとの相互作用
            - "wait": 待機

            ## ステップ出力形式
            タスク定義の例に従って、以下の形式でステップを出力してください：
            [
                {
                    "command": "navigate",
                    "x": 数値,
                    "y": 数値,
                    "z": 数値,
                    "reasoning": "このステップで達成すべき具体的な目標"
                },
                {
                    "command": "pickup",
                    "reasoning": "pickup実行で達成すべき具体的な目標"
                },
                {
                    "command": "interact",
                    "reasoning": "interact実行で達成すべき具体的な目標"
                }
            ]

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

            ## 利用可能なタスク
            {json.dumps(tasks, ensure_ascii=False, indent=2)}

            ## タスク依存関係
            {json.dumps(dependencies, ensure_ascii=False, indent=2)}

            ## タスク実行例（ステップ形式の参考）
            {json.dumps(task_examples, ensure_ascii=False, indent=2)}

            ## 利用可能なコマンド詳細
            {json.dumps(self.available_commands, ensure_ascii=False, indent=2)}

            現在の状況から最も適切なタスクを選択し、タスク実行例の形式に従ってステップシーケンスを作成してください。
            各ステップにはreasoningを必ず含めて、そのステップで何を達成するかを明確にしてください。

            出力はステップシーケンスの配列のみとしてください。
            """
            
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1500,
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
            return [{"command": "wait", "reasoning": f"エラーが発生: {str(e)}"}]
    
    def _validate_steps(self, steps: List[Dict]) -> List[Dict]:
        """ステップの妥当性をチェック"""
        validated_steps = []
        valid_commands = list(self.available_commands.keys())
        
        for step in steps:
            command = step.get("command")
            if command in valid_commands:
                validated_steps.append(step)
            else:
                logger.warning(f"Invalid command in step: {command}")
                # 無効なコマンドを待機に置き換え
                step["command"] = "wait"
                step["reasoning"] = f"無効なコマンド ({command}) のため待機"
                validated_steps.append(step)
        
        return validated_steps
    
    def _extract_steps_from_response(self, response_text: str) -> List[Dict]:
        """LLM応答からステップ配列を抽出"""
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
            return [{"command": "wait", "reasoning": "ステップ解析失敗"}]


class StepCompletionCheckerLLM:
    """Step Completion Checker LLM - ステップ完了判定と次ステップ進行判断"""
    
    def check_step_completion(self, step_info: Dict, execution_result: Dict, openai_client) -> Dict:
        """
        ステップの完了状況を分析し、次の行動を判断
        
        Args:
            step_info: 実行されたステップ情報
            execution_result: Unity側からの実行結果
            openai_client: OpenAIクライアント
            
        Returns:
            進行判断結果
        """
        try:
            system_prompt = """
            あなたはStep Completion Checker LLMです。ステップの実行結果を分析し、次の行動を決定してください。

            ## 役割
            ステップのreasoningが達成されたかを判定し、次のステップに進むか、ステップの再構築が必要かを判断する

            ## 判断基準
            ### ステップの成功判定:
            - **reasoning達成**: ステップのreasoningで設定した目標が達成されたか
            - 例: reasoning「テレビに隣接してinteractコマンドが使用可能になる」
              → Unity側でinteractコマンドが利用可能になったら成功
            - 例: reasoning「椅子を持っている状態になる」
              → プレイヤーが椅子を持った状態になったら成功

            ### 判断結果:
            - **proceed**: reasoningが達成され、次のステップに進める
            - **rebuild**: reasoningが達成されておらず、ステップの再構築が必要

            ## 出力形式
            {
                "action": "proceed" または "rebuild",
                "reasoning": "判断の理由の詳細説明"
            }
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
                "reasoning": f"エラーが発生: {str(e)}"
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
                "reasoning": "JSON解析失敗"
            }


class LLMManager:
    """2つのLLMシステムの統合管理"""
    
    def __init__(self):
        self.planner = TaskStepPlannerLLM()
        self.checker = StepCompletionCheckerLLM()
    
    def plan_task(self, current_situation: Dict, openai_client) -> List[Dict]:
        """タスク計画 (Task & Step Planner LLM使用)"""
        return self.planner.plan_task_steps(current_situation, openai_client)
    
    def check_completion(self, step_info: Dict, execution_result: Dict, openai_client) -> Dict:
        """完了チェック (Step Completion Checker LLM使用)"""
        return self.checker.check_step_completion(step_info, execution_result, openai_client)

# グローバルLLMマネージャーインスタンス
llm_manager = LLMManager()