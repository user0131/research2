"""
LLMコマンド決定器モジュール（3ステップ改良版）
Step1: 分析、Step2: タスク選択、Step3: コマンド決定
"""

import re
import json
import logging
from typing import Dict, List, Optional
try:
    # Docker環境でのインポート
    from task_definitions import (
        get_goal, get_tasks, get_dependencies, 
        get_task_description, get_task_dependencies,
        get_task_examples, get_task_example
    )
    from analysis_storage import storage
except ImportError:
    # 開発環境でのインポート
    from .task_definitions import (
        get_goal, get_tasks, get_dependencies, 
        get_task_description, get_task_dependencies,
        get_task_examples, get_task_example
    )
    from .analysis_storage import storage

# ログレベル設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMCommandDecider:
    def __init__(self):
        self.valid_commands = ["+X", "-X", "+Z", "-Z", "pickup", "interact", "wait"]
        
    def analyze_logs_and_decide(self, logs, openai_client, log_context=None):
        """
        新しい3段階のLLMシステムで分析・決定を行う
        Step1: DAGとタスクの分析・管理、Step2: タスクの現状を保存、Step3: コマンド決定・実行
        """
        try:
            # デバッグ: Unity からのメッセージを確認
            logger.info(f"Received logs: {logs}")
            
            # タスク完了状態をチェック
            completed_task = check_task_completion_criteria(logs)
            if completed_task:
                logger.info(f"Task {completed_task} has been completed!")
            
            # Step1: ログとタスクの分析・管理（DAGベース）
            step1_result = self._step1_analyze_logs_and_tasks(logs, openai_client, log_context)
            logger.info(f"Step1 - DAG Analysis & Task Management: {step1_result.get('situation_summary', 'No summary')}")
            
            # Step2: タスクの現状を保存
            step2_result = self._step2_save_task_state(step1_result)
            logger.info(f"Step2 - Task State Saved: analysis={step2_result.get('analysis_saved')}, state={step2_result.get('state_saved')}")
            
            # Step3: コマンド決定・実行
            step3_result = self._step3_decide_command(step1_result, step2_result, openai_client)
            logger.info(f"Step3 - Command Decision: {step3_result.get('command', 'wait')}")
            
            # 現在のタスクグループを取得
            current_group = get_current_task_group()
            group_progress = get_task_group_progress(current_group) if current_group != "completed" else None
            
            # 統合された推論文を構築
            integrated_reasoning = self._build_integrated_reasoning(step1_result, step2_result, step3_result)
            
            # 結果を統合してUnity用のレスポンスを作成
            response = {
                "success": True,
                "command": step3_result.get("command", "wait"),
                "reasoning": integrated_reasoning,
                "current_task": step1_result.get("current_task", "unknown"),
                "progress": step1_result.get("progress", "不明"),
                "current_group": current_group,
                "group_progress": group_progress,
                
                # デバッグ情報（追加）
                "dag_analysis": step1_result.get("dag_analysis", {}),
                "task_decision": step1_result.get("task_decision", {}),
                "save_status": {
                    "analysis_saved": step2_result.get("analysis_saved", False),
                    "state_saved": step2_result.get("state_saved", False)
                }
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error in analyze_logs_and_decide: {str(e)}")
            return {
                "success": False,
                "command": "wait",
                "reasoning": f"システムエラーが発生しました: {str(e)}",
                "current_task": "unknown",
                "progress": "エラー状態",
                "error_details": str(e)
            }
    
    def _step1_analyze_logs_and_tasks(self, logs, openai_client, log_context=None):
        """
        Step1: ログとタスクの分析・管理
        DAGとタスクの現状分析、過去の分析結果との統合、タスクレベルの決定を行う
        """
        # 現在のタスク状況を取得
        available_tasks = get_available_tasks()
        progress_summary = get_task_progress_summary()
        current_state = storage.get_current_state()
        
        # 過去の分析結果を取得（最新10件）
        recent_analyses = storage.get_recent_analyses(limit=10)
        
        # 現在のタスクに関連する過去の分析を取得
        current_task = get_next_available_task()
        task_specific_analyses = []
        if current_task:
            task_specific_analyses = storage.get_analyses_by_task(current_task)
        
        system_prompt = """
        あなたはDAGベースのタスク分析・管理の専門家です。以下の情報を包括的に分析し、DAGで定義されたタスクの現状を整理してください。

        ## Step1の役割（重要）
        1. **現在のログ分析**: Unityから送信された最新のゲーム状況の解析
        2. **DAGとタスクの現状把握**: バックエンドで保存しているタスクの有向非環グラフと進捗状況の確認
        3. **過去の分析結果との統合**: AIエージェントが過去に送信したログの分析データとの整合性確保
        4. **タスクレベルの決定**: 現状のタスクを継続するか、次のタスクに移行するかの戦略的判断

        ## 分析対象データ
        - **現在のログ**: 最新のプレイヤー状況、オブジェクト配置、利用可能コマンド
        - **DAG構造**: タスク間の依存関係と実行順序
        - **タスクの進捗状況**: 各タスクの完了状態と現在の進行状況
        - **過去の分析結果**: 過去のAIエージェントの判断履歴と学習データ
        - **保存された状態**: バックエンドに永続化された状態情報

        ## タスクレベルの判断基準
        1. **継続条件**: 現在のタスクが順調に進行中で、完了が見込める
        2. **移行条件**: 現在のタスクが完了した、または効率的な代替タスクが利用可能
        3. **依存関係**: DAGで定義された前提条件が満たされているか
        4. **効率性**: 現在の状況で最も効率的に進められるタスクはどれか

        ## 分析する要素
        - プレイヤーの現在位置と所持アイテム
        - 周辺オブジェクトの配置と利用可能性
        - 利用可能なコマンド（interact、pickup、移動コマンド）
        - DAGにおける現在のタスクの位置と依存関係
        - 過去の試行から学んだ効果的なアプローチ
        - タスク完了条件の達成状況

        ## 判定ルール（コマンド準備状況）
        **重要**: 必ずUnityから送信された「可能なコマンド」リストのみを参照してください
        
        - **interaction_ready**: Unityの「可能なコマンド」に「interact」が明示的に含まれている場合のみtrue
        - **pickup_ready**: 以下を満たす場合のみtrue
          * Unityの「可能なコマンド」に「pickup」が明示的に含まれている
          * かつ、pickupが必要な状況（アイテムを拾う/置く）である
        - **movement_needed**: 上記が両方falseの場合のみtrue
        
        **注意**: コマンドの可用性は必ずUnityログの「可能なコマンド」セクションで確認してください。
        このリストに含まれていないコマンドは使用できません。

        ## 出力形式
        以下のJSON形式で包括的な分析結果を出力してください：
        {{
            "dag_analysis": {{
                "current_task_in_dag": "DAGにおける現在のタスクの位置",
                "completed_tasks": ["完了済みタスクのリスト"],
                "dependency_status": "依存関係の満足状況",
                "next_possible_tasks": ["実行可能な次のタスク候補"]
            }},
            "task_decision": {{
                "selected_task": "選択されたタスクID",
                "decision_reasoning": "タスク選択の理由",
                "continue_current": "現在のタスクを継続するか（true/false）",
                "task_transition": "タスク移行が発生したか（true/false）"
            }},
            "current_situation": {{
                "player_position": {{"x": 数値, "z": 数値}},
                "holding_item": "持っているアイテム（なければnull）",
                "available_commands": ["利用可能なコマンドのリスト"],
                "target_object": "現在のタスクの対象オブジェクト",
                "target_position": "目標オブジェクトの相対位置情報"
            }},
            "action_analysis": {{
                "interaction_ready": "操作可能な状態か（true/false）",
                "pickup_ready": "アイテム持ち上げ可能な状態か（true/false）",
                "movement_needed": "移動が必要か（true/false）",
                "required_actions": ["必要な行動のリスト"],
                "next_immediate_action": "次に実行すべき具体的な行動"
            }},
            "historical_integration": {{
                "learned_patterns": "過去の分析から学んだパターン",
                "avoided_mistakes": "回避すべき過去の失敗",
                "successful_strategies": "成功した戦略"
            }},
            "situation_summary": "現在の状況の包括的な要約",
            "progress": "DAGにおける全体的な進捗状況"
        }}
        """
        
        # ログを結合してテキストにする
        log_text = "\n".join(logs) if logs else ""
        
        # 過去の分析結果をテキスト化
        recent_analyses_text = ""
        if recent_analyses:
            recent_analyses_text = f"""
## 過去の分析結果（最新10件）
{json.dumps(recent_analyses, ensure_ascii=False, indent=2)}
"""
        
        # 現在のタスクに関連する過去の分析
        task_analyses_text = ""
        if task_specific_analyses:
            task_analyses_text = f"""
## 現在のタスクに関連する過去の分析
{json.dumps(task_specific_analyses, ensure_ascii=False, indent=2)}
"""
        
        # 現在の状態情報
        current_state_text = f"""
## 保存された現在の状態
{json.dumps(current_state, ensure_ascii=False, indent=2)}
"""
        
        # DAGと進捗情報
        dag_info = f"""
## DAG構造
{task_dag}

## 利用可能なタスク
{json.dumps(available_tasks, ensure_ascii=False, indent=2)}

## 全体の進捗
{json.dumps(progress_summary, ensure_ascii=False, indent=2)}

## タスクの依存関係
{json.dumps(dependencies, ensure_ascii=False, indent=2)}
"""
        
        user_prompt = f"""以下の情報を包括的に分析し、DAGで定義されたタスクの現状を整理してください。

## 分析のポイント
1. **DAGにおける現在位置**: どのタスクが完了し、現在どのタスクを実行中か
2. **タスクレベルの決定**: 現在のタスクを継続するか、次のタスクに移行するか
3. **過去の学習活用**: 過去の分析から得られた知見を現在の判断に活用
4. **効率的な進行**: DAGに従った最も効率的なタスク実行計画

## 現在のログ
{log_text}

{dag_info}

{current_state_text}

{recent_analyses_text}

{task_analyses_text}"""
        
        response = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1500,
            temperature=0.1
        )
        
        response_text = response.choices[0].message.content
        result = self._extract_json_from_response(response_text)
        
        # 分析結果を構造化
        structured_result = {
            "dag_analysis": result.get("dag_analysis", {}),
            "task_decision": result.get("task_decision", {}),
            "current_situation": result.get("current_situation", {}),
            "action_analysis": result.get("action_analysis", {}),
            "historical_integration": result.get("historical_integration", {}),
            "situation_summary": result.get("situation_summary", ""),
            "progress": result.get("progress", progress_summary),
            
            # 下位互換性のために追加（Step3で使用）
            "current_task": result.get("task_decision", {}).get("selected_task", current_task),
            "interaction_ready": result.get("action_analysis", {}).get("interaction_ready", False),
            "pickup_ready": result.get("action_analysis", {}).get("pickup_ready", False),
            "movement_needed": result.get("action_analysis", {}).get("movement_needed", True),
            "target_position": result.get("current_situation", {}).get("target_position", ""),
            "available_commands": result.get("current_situation", {}).get("available_commands", [])
        }
        
        return structured_result
    
    def _step2_save_task_state(self, step1_result):
        """
        Step2: タスクの現状を保存
        Step1で分析・決定されたタスクの現状をバックエンドに永続化する
        """
        try:
            # Step1の分析結果から保存するデータを構築
            analysis_data = {
                "step": "step1_analysis",
                "dag_analysis": step1_result.get("dag_analysis", {}),
                "task_decision": step1_result.get("task_decision", {}),
                "current_situation": step1_result.get("current_situation", {}),
                "action_analysis": step1_result.get("action_analysis", {}),
                "historical_integration": step1_result.get("historical_integration", {}),
                "situation_summary": step1_result.get("situation_summary", ""),
                "progress": step1_result.get("progress", {}),
                "current_task": step1_result.get("current_task")
            }
            
            # 分析結果をストレージに保存
            save_success = storage.save_analysis(analysis_data)
            
            # 現在の状態を更新
            current_state = {
                "current_task": step1_result.get("current_task"),
                "task_progress": step1_result.get("progress", {}),
                "player_state": {
                    "position": step1_result.get("current_situation", {}).get("player_position", {}),
                    "holding_item": step1_result.get("current_situation", {}).get("holding_item"),
                    "available_commands": step1_result.get("current_situation", {}).get("available_commands", [])
                },
                "environment_state": {
                    "target_object": step1_result.get("current_situation", {}).get("target_object"),
                    "target_position": step1_result.get("current_situation", {}).get("target_position")
                },
                "dag_status": step1_result.get("dag_analysis", {}),
                "action_readiness": {
                    "interaction_ready": step1_result.get("interaction_ready", False),
                    "pickup_ready": step1_result.get("pickup_ready", False),
                    "movement_needed": step1_result.get("movement_needed", True)
                }
            }
            
            # 現在の状態を保存
            state_save_success = storage.save_current_state(current_state)
            
            # 保存結果を構築
            save_result = {
                "analysis_saved": save_success,
                "state_saved": state_save_success,
                "save_timestamp": storage._generate_analysis_id(),
                "saved_task": step1_result.get("current_task"),
                "task_transition": step1_result.get("task_decision", {}).get("task_transition", False)
            }
            
            if save_success and state_save_success:
                logger.info(f"Step2: Successfully saved analysis and state for task {step1_result.get('current_task')}")
            else:
                logger.warning(f"Step2: Partial save failure - analysis: {save_success}, state: {state_save_success}")
            
            return save_result
            
        except Exception as e:
            logger.error(f"Step2: Error saving task state: {str(e)}")
            return {
                "analysis_saved": False,
                "state_saved": False,
                "save_timestamp": None,
                "saved_task": step1_result.get("current_task"),
                "error": str(e)
            }
    
    def _step3_decide_command(self, step1_result, step2_result, openai_client):
        """
        Step3: 具体的なコマンドを決定
        Step1の分析結果のみに基づく具体的コマンド決定と行動指示を生成
        """
        system_prompt = """
        あなたはコマンド決定の専門家です。Step1の分析結果に基づいて、最適なコマンドを決定してください。

        ## Step3の役割（重要）
        - **具体的なコマンドの決定**: +X/-X/+Z/-Z/pickup/interact/wait
        - **行動内容の決定**: 具体的に何をするかの指示
        - **移動方向の計算**: 座標から適切な移動方向を計算
        - **コマンドの実行順序**: 優先順位に基づいた最適な選択

        ## 利用可能なコマンド
        - "+Z" (Z軸正方向へ移動)
        - "-Z" (Z軸負方向へ移動)
        - "+X" (X軸正方向へ移動)
        - "-X" (X軸負方向へ移動)
        - "pickup" (アイテムを拾う/置く)
        - "interact" (アイテムと相互作用)
        - "wait" (待機)

        ## 決定の優先順位（必須）
        **以下の順序で必ず判定し、条件に合致する最初のコマンドを選択する**：

        1. **interact優先**: 
           - Step1でinteraction_ready == trueの場合 → **必ず "interact"**
           - **但し**: Unityログで「interact」が利用可能コマンドに含まれている場合のみ

        2. **pickup優先**:
           - Step1でpickup_ready == trueの場合 → **必ず "pickup"**
           - **但し**: Unityログで「pickup」が利用可能コマンドに含まれている場合のみ

        3. **移動のみ**:
           - 上記のinteractとpickupが両方ともfalseの場合のみ移動コマンドを選択
           - target_positionから数値計算を実行
           - 絶対値比較で大きい方の方向を選択

        **最重要**: コマンドを決定する前に、必ずUnityから送信された利用可能コマンドリストを確認してください。
        リストに含まれていないコマンドは絶対に選択しないでください。

        ## 移動方向の計算方法（必須）
        移動が必要な場合は、以下の手順で必ず計算してください：
        
        1. **ログから相対位置を抽出**: 「x方向に-3.2、z方向に+3.4」のような情報を探す
        2. **x方向の判定**: 
           - 正の値（例：+3.2）→ +X
           - 負の値（例：-3.2）→ -X
        3. **z方向の判定**:
           - 正の値（例：+3.4）→ +Z
           - 負の値（例：-3.4）→ -Z
        4. **絶対値比較**: |x方向| と |z方向| を比較し、大きい方を選択
        5. **コマンド決定**: 選択された方向をコマンドとして出力

        **具体例**：
        - 「x方向に-3.2、z方向に+1.0に運搬可能な椅子」
        - x方向 = -3.2 → -X
        - z方向 = +1.0 → +Z
        - 絶対値比較 |3.2| > |1.0| → -X が優先
        - command = "-X"

        **重要な計算ルール**：
        - 相対位置の数値の符号を正確に判定する
        - 絶対値比較で大きい方の方向を選択する
        - 符号に基づいて+X/-X/+Z/-Zを決定する
        - 計算結果を必ずdirection_calculationに記録する

        **座標系**:
        - +X = X軸正方向
        - -X = X軸負方向
        - +Z = Z軸正方向
        - -Z = Z軸負方向

        ## 出力形式
        {{
            "command": "実行するコマンド",
            "reasoning": "このコマンドを選択した理由（Step1の分析結果を参照）",
            "action_description": "実行する行動の説明",
            "expected_outcome": "このコマンドの実行で期待される結果",
            "task_alignment": "現在のタスクとの整合性",
            "expected_actions": ["このコマンドで実行される具体的な行動のリスト"],
            "direction_calculation": {{
                "raw_position": "ログから抽出した相対位置の文字列",
                "x_direction": "x方向の数値",
                "z_direction": "z方向の数値",
                "x_direction_name": "x方向の名前（+X/-X）",
                "z_direction_name": "z方向の名前（+Z/-Z）",
                "chosen_direction": "選択された方向",
                "calculation_used": "計算が使用されたかどうか（true/false）"
            }}
        }}
        """
        
        user_prompt = f"""
        ## Step1の分析結果
        {json.dumps(step1_result, ensure_ascii=False, indent=2)}

        ## Step2の保存結果
        {json.dumps(step2_result, ensure_ascii=False, indent=2)}

        上記のStep1の分析結果に基づいて、次に実行すべき具体的なコマンドを決定してください。

        **最重要原則：必ず以下の順序で判定する**

        ## 判定手順（必須）
        1. **Step1のinteraction_ready をチェック**:
           - true の場合 → **"interact" を選択して終了**
        
        2. **Step1のpickup_ready をチェック**:
           - true の場合 → **"pickup" を選択して終了**
        
        3. **両方ともfalseの場合のみ移動コマンドを選択**:
           - target_positionから数値計算を実行
           - 絶対値比較で大きい方の方向を選択

        **重要**: Step1の判定結果（interaction_ready, pickup_ready）を絶対的に信頼してください。

        特に以下の情報を重視してください：
        1. **Step1の行動分析**: interaction_ready, pickup_ready, movement_needed
        2. **現在の状況**: available_commands, target_position
        3. **数値計算結果**: target_positionの数値から算出される移動方向
        4. **選択されたタスク**: current_task, task_decision

        **移動方向の決定は必ず以下の手順で行う**：
        1. ログから「x方向に[数値]、z方向に[数値]」を抽出
        2. 数値の符号を判定（+は正方向、-は負方向）
        3. 絶対値比較で大きい方を選択
        4. 符号に基づいて+X/-X/+Z/-Zを決定

        **移動が必要な場合の計算例**：
        現在のログに「x方向に-3.2、z方向に+2.1に運搬可能な椅子」がある場合：
        - x方向: -3.2（負の値）→ -X
        - z方向: +2.1（正の値）→ +Z
        - 絶対値: |3.2| > |2.1| → -X を選択
        - コマンド: "-X"

        **重要**: 移動方向の計算は必ず数値の符号と絶対値を正確に判定してください。

        選択されたタスクを効率的に進めるための最適なコマンドと、そのコマンドで実行される具体的な行動内容を決定してください。
        """
        
        response = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=800,
            temperature=0.2
        )
        
        response_text = response.choices[0].message.content
        result = self._extract_json_from_response(response_text)
        
        # Step1の結果から実際に利用可能なコマンドを取得
        available_commands = step1_result.get("available_commands", [])
        
        # コマンドの妥当性をチェック
        selected_command = result.get("command")
        if selected_command not in self.valid_commands:
            logger.warning(f"Invalid command (not in valid_commands): {selected_command}, defaulting to wait")
            result["command"] = "wait"
            result["reasoning"] = f"無効なコマンド（システムで未定義）のため待機: {selected_command}"
        elif selected_command not in available_commands and selected_command != "wait":
            # Unityから送信された利用可能コマンドリストにも含まれていない場合
            logger.warning(f"Command not available in Unity: {selected_command}, available: {available_commands}")
            result["command"] = "wait"
            result["reasoning"] = f"Unityで利用不可能なコマンドのため待機: {selected_command}（利用可能: {available_commands}）"
        
        return result

    def _extract_json_from_response(self, response_text):
        """
        GPTの応答からJSON部分を抽出
        """
        try:
            # まずは直接JSONとして解析を試行
            return json.loads(response_text)
        except json.JSONDecodeError:
            # コードブロック内のJSONを探す
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # 最後の手段として、JSONらしい部分を探す
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
            
            # すべて失敗した場合はデフォルト値を返す
            logger.warning(f"Failed to extract JSON from response: {response_text}")
            return {
                "reasoning": "JSONの解析に失敗しました",
                "command": "wait",
                "current_task": "unknown",
                "progress": "エラー"
            }

    def _build_integrated_reasoning(self, step1_result, step2_result, step3_result):
        """
        3つのステップの結果を統合して読みやすい推論文を作成
        """
        try:
            # Step1の分析サマリー
            step1_summary = step1_result.get("situation_summary", "状況分析なし")
            
            # DAG分析情報
            dag_info = step1_result.get("dag_analysis", {})
            current_task_in_dag = dag_info.get("current_task_in_dag", "不明")
            
            # タスク決定情報
            task_decision = step1_result.get("task_decision", {})
            selected_task = task_decision.get("selected_task", "不明")
            decision_reasoning = task_decision.get("decision_reasoning", "")
            
            # Step2の保存状況
            save_status = "保存成功" if step2_result.get("analysis_saved", False) and step2_result.get("state_saved", False) else "保存失敗"
            
            # Step3のコマンド決定
            command = step3_result.get("command", "wait")
            command_reasoning = step3_result.get("reasoning", "理由なし")
            action_description = step3_result.get("action_description", "")
            
            # 統合された推論文を構築
            integrated_reasoning = f"""
【Step1: DAG分析・タスク管理】
現在の状況: {step1_summary}
DAGでの位置: {current_task_in_dag}
選択されたタスク: {selected_task}
決定理由: {decision_reasoning}

【Step2: 状態保存】
保存状況: {save_status}

【Step3: コマンド決定】
選択コマンド: {command}
実行内容: {action_description}
決定理由: {command_reasoning}
            """.strip()
            
            return integrated_reasoning
            
        except Exception as e:
            logger.error(f"Error building integrated reasoning: {str(e)}")
            return f"推論文の構築に失敗: {str(e)}"

    def get_task_status(self, logs):
        """
        タスクの状態を取得 - 細分化されたタスクに対応
        """
        try:
            # 最新のタスク進捗を取得
            progress = get_task_progress_summary()
            current_task = get_next_available_task()
            current_group = get_current_task_group()
            
            return {
                "current_task": current_task,
                "current_group": current_group,
                "progress": progress,
                "completed_tasks": [task for task, completed in progress.get('task_status', {}).items() if completed],
                "remaining_tasks": [task for task, completed in progress.get('task_status', {}).items() if not completed]
            }
            
        except Exception as e:
            logger.error(f"Error getting task status: {str(e)}")
            return {
                "current_task": "unknown",
                "current_group": "unknown",
                "progress": {"completed": 0, "total": 10, "percentage": 0},
                "completed_tasks": [],
                "remaining_tasks": []
            }