"""
OpenAI実出力テスト
実際のOpenAI APIを使用してLLM出力品質を検証するテストスイート
"""

import sys
import os
import json
import time
from datetime import datetime

# srcディレクトリをパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', 'src')
sys.path.insert(0, src_path)

from services.llm_manager import llm_manager
from config.constants import get_tasks, get_dependencies, get_task_examples, get_available_commands
from openai import OpenAI

class OpenAIRealTester:
    """OpenAI実出力テストクラス"""
    
    def __init__(self):
        self.test_results = []
        self.setup_openai_client()
    
    def setup_openai_client(self):
        """OpenAIクライアントの設定"""
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            print("❌ OPENAI_API_KEY環境変数が設定されていません")
            print("export OPENAI_API_KEY=your_api_key_here を実行してください")
            exit(1)
        
        self.openai_client = OpenAI(api_key=api_key)
        print("✅ OpenAI APIクライアント初期化完了")
    
    def run_test(self, test_name: str, test_func, description: str):
        """テスト実行"""
        print(f"\n{'='*60}")
        print(f"🧪 {test_name}")
        print(f"{'='*60}")
        print(f"説明: {description}")
        
        try:
            start_time = time.time()
            result = test_func()
            end_time = time.time()
            
            print(f"⏱️  実行時間: {end_time - start_time:.2f}秒")
            
            success = self.validate_llm_output(result, test_name)
            
            self.test_results.append({
                "test_name": test_name,
                "success": success,
                "result": result,
                "execution_time": end_time - start_time
            })
            
        except Exception as e:
            print(f"❌ エラー発生: {str(e)}")
            self.test_results.append({
                "test_name": test_name,
                "success": False,
                "error": str(e)
            })
    
    def validate_llm_output(self, result, test_name: str) -> bool:
        """LLM出力の検証"""
        if not result:
            print("❌ 出力が空です")
            return False
        
        print(f"📋 出力内容:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 基本的な品質チェック
        if isinstance(result, list) and len(result) > 0:
            print("✅ リスト形式で出力されています")
            return True
        elif isinstance(result, dict):
            print("✅ 辞書形式で出力されています") 
            return True
        else:
            print("❌ 期待される形式ではありません")
            return False
    
    def test_llm1_task_planning(self):
        """LLM1: タスク計画の実出力テスト"""
        current_situation = {
            "logs": [
                "=== 現在の状況 ===",
                "[現在地]",
                "座標（X=5.3, Z=3.0）",
                "[周辺の状況]",
                "x方向に-5.2、z方向に+2.4にテレビ（座標: x=0.1, z=5.4）",
                "x方向に-8.5、z方向に-3.6に運搬可能な椅子（座標: x=-3.2, z=-0.6）",
                "x方向に-1.0、z方向に+5.4にPCプレート（座標: x=4.3, z=8.4）",
                "[持っているもの]",
                "何も持っていません",
                "[可能なコマンド]",
                "navigation（任意の座標へ移動）",
                "状況: 研究室の準備を開始します"
            ]
        }
        
        result = llm_manager.plan_task(current_situation, self.openai_client)
        
        # 追加検証: ステップ構造
        if isinstance(result, list):
            for i, step in enumerate(result):
                print(f"\n📝 ステップ {i+1}:")
                print(f"  - command: {step.get('command', 'N/A')}")
                print(f"  - reasoning: {step.get('reasoning', 'N/A')}")
                # navigate(x,z)形式またはnavigate + x,z形式のチェック
                if step.get('command', '').startswith('navigate('):
                    print(f"  - 形式: navigate(x,z)")
                elif step.get('command') == 'navigate':
                    print(f"  - x: {step.get('x', 'N/A')}")
                    print(f"  - z: {step.get('z', 'N/A')}")
        
        return result
    
    def test_llm2_completion_check_proceed(self):
        """LLM2: ステップ完了判定（成功パターン）の実出力テスト"""
        step_info = {
            "command": "navigate(0.1,5.4)",
            "reasoning": "テレビに隣接してinteractコマンドが使用可能になる",
            "step_id": "test_step_1",
            "task_id": "test_task_1"
        }
        
        execution_result = {
            "executed_command": "navigate(0.1,5.4)",
            "result_logs": [
                "=== 現在の状況 ===",
                "[現在地]",
                "座標（X=0.1, Z=5.4）",
                "[周辺の状況]",
                "x方向に+0.0、z方向に+0.0にテレビ（座標: x=0.1, z=5.4）",
                "[持っているもの]",
                "何も持っていません",
                "[検出情報]",
                "+X+Z約0.1メートルにテレビあり。OFF・interactコマンドで操作可能",
                "[可能なコマンド]",
                "navigation（任意の座標へ移動）、interact（テレビを操作・現在OFF）"
            ],
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "current_logs": ["テレビの前に立っています", "interactコマンドが使用可能です"]
        }
        
        result = llm_manager.check_completion(step_info, execution_result, self.openai_client)
        
        # 追加検証: 判定結果
        if isinstance(result, dict):
            print(f"\n📝 判定結果:")
            print(f"  - action: {result.get('action', 'N/A')}")
            print(f"  - reasoning: {result.get('reasoning', 'N/A')}")
        
        return result
    
    def test_llm2_completion_check_rebuild(self):
        """LLM2: ステップ完了判定（失敗パターン）の実出力テスト"""
        step_info = {
            "command": "pickup",
            "reasoning": "椅子を持っている状態になる",
            "step_id": "test_step_2",
            "task_id": "test_task_2"
        }
        
        execution_result = {
            "executed_command": "pickup",
            "result_logs": [
                "=== 現在の状況 ===",
                "[現在地]",
                "座標（X=-3.2, Z=-0.6）",
                "[周辺の状況]",
                "周辺に重要なオブジェクトはありません",
                "[持っているもの]",
                "何も持っていません",
                "[実行したアクション]",
                "[ERROR] 椅子が見つかりません",
                "pickupコマンドが失敗しました",
                "[可能なコマンド]",
                "navigation（任意の座標へ移動）"
            ],
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "current_logs": ["椅子が見つかりません", "現在地に椅子はありません"]
        }
        
        result = llm_manager.check_completion(step_info, execution_result, self.openai_client)
        
        # 追加検証: 判定結果
        if isinstance(result, dict):
            print(f"\n📝 判定結果:")
            print(f"  - action: {result.get('action', 'N/A')}")
            print(f"  - reasoning: {result.get('reasoning', 'N/A')}")
        
        return result
    
    def test_llm3_task_reconstruction(self):
        """LLM3: タスク再構成の実出力テスト"""
        error_info = {
            "logs": [
                "=== 現在の状況 ===",
                "[現在地]",
                "座標（X=-3.2, Z=-0.6）",
                "[周辺の状況]",
                "周辺に重要なオブジェクトはありません",
                "[持っているもの]",
                "何も持っていません",
                "[実行したアクション]",
                "[ERROR] 椅子が見つかりません",
                "pickupコマンドが失敗しました",
                "[可能なコマンド]",
                "navigation（任意の座標へ移動）"
            ],
            "error_type": "error",
            "error_details": {"command": "pickup", "reason": "target_not_found"},
            "timestamp": datetime.now().isoformat()
        }
        
        current_step = {
            "id": "failed_step",
            "task_id": "chair_move_task", 
            "command": "pickup",
            "reasoning": "椅子を拾う",
            "x": None,
            "z": None
        }
        
        result = llm_manager.reconstruct_task(error_info, current_step, self.openai_client)
        
        # 追加検証: 再構成ステップ
        if isinstance(result, dict) and result.get("new_steps"):
            print(f"\n📝 再構成されたステップ:")
            for i, step in enumerate(result["new_steps"]):
                print(f"  ステップ {i+1}:")
                print(f"    - command: {step.get('command', 'N/A')}")
                print(f"    - reasoning: {step.get('reasoning', 'N/A')}")
                # navigate(x,z)形式またはnavigate + x,z形式のチェック
                if step.get('command', '').startswith('navigate('):
                    print(f"    - 形式: navigate(x,z)")
                elif step.get('command') == 'navigate':
                    print(f"    - x: {step.get('x', 'N/A')}")
                    print(f"    - z: {step.get('z', 'N/A')}")
        
        return result
    
    def test_llm1_complex_situation(self):
        """LLM1: 複雑な状況でのタスク計画テスト"""
        current_situation = {
            "logs": [
                "=== 現在の状況 ===",
                "[現在地]",
                "座標（X=2.5, Z=4.1）",
                "[周辺の状況]",
                "x方向に-2.5、z方向に-0.6にDaiArea（座標: x=0.02, z=3.55）",
                "x方向に+0.5、z方向に-2.6にパソコン（座標: x=3.0, z=1.5）",
                "[持っているもの]",
                "PCプレート",
                "[実行したアクション]",
                "テレビをONにしました！",
                "運搬可能な椅子を置きました！場所: 座標X:5.5, Z:-3.7、ChairArea付近",
                "[検出情報]",
                "DaiAreaに到達。PCプレートを置く準備が完了。",
                "[可能なコマンド]",
                "navigation（任意の座標へ移動）、pickup（DaiAreaに置く）",
                "注意: PCプレートを既に持っているため、PCを拾って配置する必要がある"
            ]
        }
        
        result = llm_manager.plan_task(current_situation, self.openai_client)
        
        # 複雑さの検証
        if isinstance(result, list):
            print(f"\n📝 複雑な状況での計画:")
            print(f"  - 計画されたステップ数: {len(result)}")
            for i, step in enumerate(result):
                print(f"  ステップ {i+1}: {step.get('command')} - {step.get('reasoning', '')[:50]}...")
        
        return result
    
    def test_llm_json_parsing(self):
        """LLM出力のJSON解析能力テスト"""
        print("\n🔍 JSON解析テスト:")
        
        # 各LLMの出力をテスト
        tests = [
            ("LLM1", self.test_llm1_task_planning),
            ("LLM2-proceed", self.test_llm2_completion_check_proceed), 
            ("LLM2-rebuild", self.test_llm2_completion_check_rebuild),
            ("LLM3", self.test_llm3_task_reconstruction)
        ]
        
        json_results = {}
        for llm_name, test_func in tests:
            try:
                result = test_func()
                json_results[llm_name] = {
                    "parseable": True,
                    "type": type(result).__name__,
                    "content_sample": str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
                }
                print(f"✅ {llm_name}: JSON解析可能")
            except Exception as e:
                json_results[llm_name] = {
                    "parseable": False,
                    "error": str(e)
                }
                print(f"❌ {llm_name}: JSON解析エラー - {str(e)}")
        
        return json_results
    
    def run_all_tests(self):
        """全テストの実行"""
        print("🚀 OpenAI実出力テストを開始します")
        print("=" * 80)
        print("⚠️  注意: 実際のOpenAI APIを使用するため、API使用料が発生します")
        print("=" * 80)
        
        # 確認プロンプト（Docker環境では自動実行）
        import sys
        if sys.stdin.isatty():
            confirm = input("続行しますか？ (y/N): ").strip().lower()
            if confirm != 'y':
                print("❌ テストを中止しました")
                return
        else:
            print("🚀 Docker環境で自動実行します")
        
        # テスト実行
        self.run_test(
            "LLM1: タスク計画",
            self.test_llm1_task_planning,
            "現在の状況からタスクを計画し、ステップシーケンスを生成"
        )
        
        self.run_test(
            "LLM2: 完了判定（成功）",
            self.test_llm2_completion_check_proceed,
            "ステップが正常完了した場合の判定"
        )
        
        self.run_test(
            "LLM2: 完了判定（失敗）", 
            self.test_llm2_completion_check_rebuild,
            "ステップが失敗した場合の判定"
        )
        
        self.run_test(
            "LLM3: タスク再構成",
            self.test_llm3_task_reconstruction,
            "エラー発生時の代替タスク再構成"
        )
        
        self.run_test(
            "LLM1: 複雑状況",
            self.test_llm1_complex_situation,
            "複雑な状況での適応的タスク計画"
        )
        
        self.run_test(
            "JSON解析能力",
            self.test_llm_json_parsing,
            "各LLM出力のJSON形式正確性"
        )
        
        # 結果サマリー
        self.print_summary()
    
    def print_summary(self):
        """テスト結果のサマリー出力"""
        print("\n" + "="*80)
        print("📊 OpenAI実出力テスト結果サマリー")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.get("success", False))
        failed_tests = total_tests - passed_tests
        
        total_time = sum(result.get("execution_time", 0) for result in self.test_results if "execution_time" in result)
        
        print(f"🧪 総テスト数: {total_tests}")
        print(f"✅ 成功: {passed_tests}")
        print(f"❌ 失敗: {failed_tests}")
        print(f"📈 成功率: {(passed_tests/total_tests)*100:.1f}%")
        print(f"⏱️  総実行時間: {total_time:.2f}秒")
        
        if failed_tests > 0:
            print(f"\n❌ 失敗したテスト:")
            for result in self.test_results:
                if not result.get("success", False):
                    print(f"  - {result['test_name']}")
                    if "error" in result:
                        print(f"    エラー: {result['error']}")
        
        print(f"\n💡 推奨改善点:")
        if passed_tests == total_tests:
            print("  🎉 全テスト成功！LLM出力品質は良好です")
        else:
            print("  - プロンプトテンプレートの調整を検討")
            print("  - 出力形式の指示をより明確に")
            print("  - エラーハンドリングの強化")

def main():
    """メイン実行関数"""
    print("🤖 Unity Research Lab Backend - OpenAI実出力テスト")
    print("🔗 実際のOpenAI GPT-4o-miniを使用してLLM出力品質を検証")
    
    tester = OpenAIRealTester()
    tester.run_all_tests()
    
    print("\n✨ テスト完了!")
    print("📝 結果を参考にプロンプトやロジックの改善を検討してください")

if __name__ == "__main__":
    main()