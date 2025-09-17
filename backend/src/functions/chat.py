import os
import json
from typing import List, Dict, Optional
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class ChatWithMemory:
    def __init__(self):
        # OpenAIクライアントを初期化
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        self.client = OpenAI(api_key=api_key)
        self.conversation_history: List[Dict[str, str]] = []
        self.knowledge_path = Path("./src/functions/knowledge.txt")

        # 知識ベースを読み込んでシステムプロンプトに含める
        knowledge_content = self.knowledge()
        self.base_system_content = f"""あなたはUSERと一緒に災害対応の仕事を行う仲間（人間）です。
ユーザとの会話の文脈を記憶し、自然な対話を行います。

重要な振る舞い：
- あなたは人間として振る舞います
- 専門的な知識や詳細が必要な場合、まず「わからないですね... ○○について調べましょうか？」と提案してください
- ユーザーが「はい」「調べて」「お願い」などの肯定的な返事をした場合のみ、read_document関数を使用してください
- 調べた後は「○○のようです」という自然な形で伝えてください
- 音声での会話を想定して、自然な口調で話してください
- リストや箇条書きは避けて、流れるような会話文で応答してください

## あなたが知っている知識(参考程度に使ってください)
{knowledge_content}
"""

    def add_message(self, role: str, content: str):
        """会話履歴にメッセージを追加"""
        self.conversation_history.append({"role": role, "content": content})

    def read_document(self, query: str = "") -> str:
        """ベクトルデータベースから関連情報を取得"""
        try:
            # ベクトルデータベースから検索
            from rag_db_maker import load_retriever
            import os
            import sys

            # configからパスを取得
            sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
            from config.constants import VECTOR_DB_PATH, HIRAKATA_JISIN_VECTOR

            db_path = os.path.join(VECTOR_DB_PATH, HIRAKATA_JISIN_VECTOR)

            # ベクトルデータベースが存在するかチェック
            if not os.path.exists(db_path):
                return "ベクトルデータベースが見つかりません。先にrag_db_maker.pyを実行してください。"

            # クエリが空の場合はデフォルトクエリを使用
            if not query.strip():
                query = "災害対応の基本情報"

            # ベクトル検索実行
            retriever, _ = load_retriever(db_path)
            results = retriever.invoke(query)

            # 結果をフォーマット
            formatted_results = []
            for i, doc in enumerate(results[:3], 1):  # 上位3件
                meta = doc.metadata
                chapter = meta.get('chapter', '')
                section = meta.get('section', '')
                location = f"{chapter} / {section}" if chapter or section else f"ページ{meta.get('page_start', 'unknown')}"

                content = doc.page_content[:300]  # 300文字まで
                formatted_results.append(f"【{i}. {location}】\n{content}")

            if formatted_results:
                return f"クエリ「{query}」の検索結果:\n\n" + "\n\n".join(formatted_results)
            else:
                return f"クエリ「{query}」に関連する情報が見つかりませんでした。"

        except Exception as e:
            return f"ベクトル検索エラー: {str(e)}"

    def knowledge(self) -> str:
        """ナレッジベースの知識を取得"""
        try:
            return self.knowledge_path.read_text(encoding='utf-8')
        except Exception as e:
            return f"知識の読み込みエラー: {str(e)}"

    def get_function_definitions(self) -> List[Dict]:
        """Function calling用の関数定義を取得"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_document",
                    "description": "災害対応に関する専門的な知識や詳細な情報をベクトルデータベースから検索して取得します",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "検索したい内容やキーワード（例：災害対策本部、避難所設置、応急対策など）"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
    
    def send_message(self, user_message: str) -> str:
        """メッセージを送信してresponseを取得（function calling対応）"""
        self.add_message("user", user_message)

        try:
            system_prompt = {"role": "system", "content": self.base_system_content}
            messages = [system_prompt] + self.conversation_history

            # Function calling対応でOpenAI APIを呼び出し
            response = self.client.chat.completions.create(
                model="gpt-5-mini",
                messages=messages,
                tools=self.get_function_definitions(),
                tool_choice="auto"
            )

            response_message = response.choices[0].message

            # Tool callがあるかチェック
            if response_message.tool_calls:
                tool_call = response_message.tool_calls[0]
                function_name = tool_call.function.name

                if function_name == "read_document":
                    # 引数からクエリを取得
                    import json
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                        query = arguments.get("query", "")
                    except:
                        query = ""

                    # ベクトル検索実行
                    document_content = self.read_document(query)
                    print(f"📚 調べています... (キーワード: {query})")

                    # ドキュメント内容を含めて再度API呼び出し（履歴には追加せず直接使用）
                    messages = [system_prompt] + self.conversation_history + [
                        {"role": "assistant", "content": f"今、{query}について調べました。"},
                        {"role": "system", "content": f"以下の情報を参考に、自然な会話として回答してください：\n{document_content}"}
                    ]
                    second_response = self.client.chat.completions.create(
                        model="gpt-5-mini",
                        messages=messages
                    )

                    assistant_message = second_response.choices[0].message.content
                else:
                    assistant_message = "申し訳ありませんが、不明な関数が呼ばれました。"
            else:
                assistant_message = response_message.content

            self.add_message("assistant", assistant_message)
            return assistant_message

        except Exception as e:
            error_message = f"エラーが発生しました: {str(e)}"
            print(error_message)
            return error_message
    
    def clear_history(self):
        """会話履歴をクリア"""
        self.conversation_history = []

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """会話履歴を取得"""
        return self.conversation_history.copy()


def main():
    """メイン関数 - インタラクティブチャット"""
    print("commanda:")
    print("   /clear  - 会話履歴をクリア")
    print("   /history - 会話履歴を表示")
    print("   /exit   - 終了")

    try:
        chat = ChatWithMemory()
    except Exception as e:
        print(f"error: {e}")
        return

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() == "/exit":
                # 会話終了時のタスク分析
                conversation_history = chat.get_conversation_history()
                if conversation_history:
                    try:
                        from task_or_conv_definder import TaskOrConvDefinder
                        definder = TaskOrConvDefinder()
                        result = definder.process_conversation_end(conversation_history)

                        # 次のアクションに基づく処理
                        task_analysis = result["task_analysis"]
                        next_type = task_analysis.get("next", "")
                        detail = task_analysis.get("detail", "")

                        if next_type == "task":
                            print(f"\naiエージェントがやるタスクの詳細は以下になります:")
                            print(f"{detail}")
                        elif next_type == "conversation":
                            print(f"\n会話継続:")
                            print(f"assistant: {detail}")
                            continue

                    except Exception as e:
                        print(f"タスク分析 error: {e}")

                print("bie")
                break

            elif user_input.lower() == "/clear":
                chat.clear_history()
                print("🧹 会話履歴をクリアしました")
                continue

            elif user_input.lower() == "/history":
                history = chat.get_conversation_history()
                if history:
                    print("\n📖 会話履歴:")
                    for i, msg in enumerate(history, 1):
                        role = msg["role"].upper() 
                        if role != "SYSTEM": 
                            print(f"{role}: {msg['content']}")
                else:
                    print("会話履歴はありません")
                print()
                continue

            elif user_input:
                print("assitant ", end="", flush=True)
                response = chat.send_message(user_input)
                print(response)
                print()

        except KeyboardInterrupt:
            # Ctrl+Cでも終了時処理を実行
            conversation_history = chat.get_conversation_history()
            if conversation_history:
                try:
                    from task_or_conv_definder import TaskOrConvDefinder
                    definder = TaskOrConvDefinder()
                    definder.process_conversation_end(conversation_history)
                except Exception as e:
                    print(f"analyze error: {e}")
            print("\nbie")
            break
        except Exception as e:
            print(f"error: {e}")


if __name__ == "__main__":
    main()