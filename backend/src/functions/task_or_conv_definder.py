"""
タスク判定システム
会話内容からタスクを抽出・分類し、適切なアクションを決定する
"""

import os
import json
from typing import List, Dict, Tuple, Literal
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

class TaskAnalysisResult(BaseModel):
    next: Literal["conversation", "task"]
    detail: str

class TaskOrConvDefinder:
    def __init__(self):
        # OpenAIクライアントを初期化
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        self.client = OpenAI(api_key=api_key)
        self.document_path = Path("./document.txt")

    def read_document(self) -> str:
        """ドキュメントファイルを読み込み"""
        try:
            return self.document_path.read_text(encoding='utf-8')
        except Exception as e:
            return f"Error reading document: {str(e)}"


    def analyze_conversation_for_task(self, conversation_history: List[Dict[str, str]]) -> Dict:
        """会話履歴からタスクを分析"""
        # 会話内容を文字列に変換
        conversation_list = []
        conversation_text = ""
        for msg in conversation_history:
            role = msg.get("role", "").upper() # 大文字に統一
            content = msg.get("content", "")
            if role != "SYSTEM":  # システムメッセージは除外
                conversation_list.append(f"{role}: {content}") 
        conversation_text = "\n".join(conversation_list)

        # LLMで詳細分析
        return self._analyze_with_llm(conversation_text)

    def _analyze_with_llm(self, conversation_text: str) -> Dict:
        """LLMによる詳細分析（Structured output対応）"""
        try:
            # ドキュメント内容を常に読み込み
            document_content = self.read_document()

            system_prompt = f"""あなたは会話内容から次あなたがやることを決定する専門家です。
会話内容から、次あなたがやるべきタスクの詳細を教えてくださいください：

## 知っている知識
{document_content}

## 判定基準:
- conversation: 会話内容や自分の知っている知識では支持されたタスクをどのように進めたらいいか分からず、ユーザに聞く必要がある場合（detailには直接ユーザに送る会話メッセージを含める）
- task:会話内容をもとに、次に行うタスクがわかり、その具体的な内容までわかる場合（detailには詳細な作業手順を含める）

## 注意:
- conversationの場合、detailには、直接ユーザに送信できる自然な会話メッセージを100文字以内で記述してください
- taskの場合、detailには具体的な作業手順を記述してください
- タスクの詳細が不明な場合は推定せず、ユーザに質問する会話メッセージを生成してください
"""

            # Structured output対応でOpenAI APIを呼び出し
            response = self.client.beta.chat.completions.parse(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"以下の会話内容から、あなたが次にやるタスクの詳細を出力してください：\n\n{conversation_text}"}
                ],
                response_format=TaskAnalysisResult,
                max_completion_tokens=10000,
            )

            # Structured outputから結果を取得
            if response.choices[0].message.parsed:
                result = response.choices[0].message.parsed
                return result.model_dump()
            else:
                return {
                    "next": "conversation",
                    "detail": "応答の解析に失敗しました"
                }

        except Exception as e:
            return {
                "next": "conversation",
                "detail": f"システムエラーが発生しました: {str(e)}"
            }

    def determine_next_action(self, task_analysis: Dict) -> Tuple[str, str]:
        """次のアクションを決定"""
        next_type = task_analysis.get("next", "unknown")
        detail = task_analysis.get("detail", "")

        if next_type == "conversation":
            return "completed", f"一般的な会話として完了しました"

        elif next_type == "task" and detail:
            return "task_identified", f"タスクが特定されました"

        else:
            return "unclear", "明確なタスクが特定できませんでした"

    def process_conversation_end(self, conversation_history: List[Dict[str, str]]) -> Dict:
        """会話終了時の処理"""
        print("🔍 タスク分析を開始します...")

        # タスク分析実行
        task_analysis = self.analyze_conversation_for_task(conversation_history)
        next_action = task_analysis.get("next", "")
        detail = task_analysis.get("detail", "")


        # 結果表示
        print(f"分析結果:")
        print(f"次のアクション: {next_action}")
        print(f"詳細: {detail}")

        return {
            "next_action": task_analysis,
            "detail": detail,
        }


def main():
    """テスト用のメイン関数"""
    definder = TaskOrConvDefinder()

    # テスト用の会話履歴
    test_conversation = [
        {"role": "user", "content": "こんにちは"},
        {"role": "assistant", "content": "こんにちは！何かお手伝いできることはありますか？"},
        {"role": "user", "content": "Pythonのコードにバグがあるので修正してもらいたいです"},
        {"role": "assistant", "content": "バグの修正をお手伝いします。どのようなエラーが発生していますか？"}
    ]
    
    result = definder.process_conversation_end(test_conversation)

if __name__ == "__main__":
    main()