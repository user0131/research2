"""
LLM出力テスト
command_controllerの各アクションの出力を検証するテストスイート
"データフローと条件分岐"検証
"""

import sys
import os
import json
from unittest.mock import Mock, patch
from datetime import datetime

# srcディレクトリをパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', 'src')
sys.path.insert(0, src_path)

import command_controller
from constants import ACTIONS

class MockOpenAIClient:
    """OpenAIクライアントのモック"""
    
    def __init__(self, response_content="[]"):
        self.response_content = response_content
    
    @property
    def chat(self):
        return self
    
    @property
    def completions(self):
        return self
    
    def create(self, **kwargs):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = self.response_content
        return mock_response

class LLMOutputTester:
    """LLM出力テストクラス"""
    
    def __init__(self):
        self.test_results = []
        self.setup_mocks()
    
    def setup_mocks(self):
        """モックの設定"""
        # Step manager をリセット
        with patch('command_controller.step_manager') as mock_step_manager:
            mock_step_manager.get_queue_status.return_value = {
                "total_steps": 0,
                "status_counts": {"pending": 0, "executing": 0, "completed": 0, "failed": 0},
                "current_step_id": None,
                "has_pending_steps": False
            }
    
    def run_test(self, test_name: str, data: dict, expected_action: str, description: str):
        """テスト実行"""
        print(f"\n=== {test_name} ===")
        print(f"説明: {description}")
        print(f"入力データ: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        try:
            # OpenAIクライアントモック
            mock_client = MockOpenAIClient()
            
            # テスト実行
            result = command_controller.command_controller.process_step(data, mock_client)
            
            print(f"期待するアクション: {expected_action}")
            
            # JSON出力（MagicMock対応）
            try:
                print(f"実際の結果: {json.dumps(result, ensure_ascii=False, indent=2)}")
            except TypeError as e:
                print(f"実際の結果（JSON変換エラー）: {str(result)}")
                print(f"JSON変換エラー詳細: {str(e)}")
            
            # 結果の検証
            success = self.validate_result(result, expected_action, test_name)
            
            self.test_results.append({
                "test_name": test_name,
                "success": success,
                "expected_action": expected_action,
                "actual_result": result
            })
            
        except Exception as e:
            print(f"❌ エラー発生: {str(e)}")
            self.test_results.append({
                "test_name": test_name,
                "success": False,
                "error": str(e)
            })
    
    def validate_result(self, result: dict, expected_action: str, test_name: str) -> bool:
        """結果の検証"""
        if not isinstance(result, dict):
            print(f"❌ 結果がDict型ではありません")
            return False
        
        if "success" not in result:
            print(f"❌ successフィールドがありません")
            return False
        
        if "command" not in result:
            print(f"❌ commandフィールドがありません")
            return False
        
        # 基本的な構造チェック
        required_fields = ["success", "command", "reasoning"]
        for field in required_fields:
            if field not in result:
                print(f"❌ 必須フィールド '{field}' がありません")
                return False
        
        print(f"✅ 基本構造OK")
        return True
    
    def test_initial_planning(self):
        """初回タスク計画のテスト"""
        with patch('command_controller.step_manager') as mock_step_manager:
            # 空のキュー状態をモック
            mock_step_manager.get_queue_status.return_value = {
                "total_steps": 0,
                "status_counts": {"pending": 0, "executing": 0, "completed": 0, "failed": 0},
                "current_step_id": None,
                "has_pending_steps": False
            }
            
            # タスク追加のモック
            mock_step_manager.add_steps.return_value = ["step_1", "step_2"]
            mock_step_manager.get_next_step.return_value = {
                "id": "step_1",
                "command": "navigate",
                "x": 0.1,
                "z": 5.4,
                "reasoning": "テレビに隣接してinteractコマンドが使用可能になる"
            }
            
            data = {
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
                    "navigation（任意の座標へ移動）"
                ]
            }
            
            with patch('command_controller.llm_manager') as mock_llm:
                # LLM1のレスポンスをモック
                mock_llm.plan_task.return_value = [
                    {
                        "command": "navigate",
                        "x": 0.1,
                        "z": 5.4,
                        "reasoning": "テレビに隣接してinteractコマンドが使用可能になる"
                    }
                ]
                
                self.run_test(
                    "初回タスク計画",
                    data,
                    ACTIONS["PLANNED"],
                    "空のキューから初回タスクを計画し、最初のステップを返す"
                )
    
    def test_get_next_step(self):
        """次ステップ取得のテスト"""
        with patch('command_controller.step_manager') as mock_step_manager:
            # ペンディングステップありの状態をモック
            mock_step_manager.get_queue_status.return_value = {
                "total_steps": 3,
                "status_counts": {"pending": 2, "executing": 0, "completed": 1, "failed": 0},
                "current_step_id": None,
                "has_pending_steps": True
            }
            
            mock_step_manager.get_next_step.return_value = {
                "id": "step_2",
                "command": "pickup",
                "reasoning": "椅子を持っている状態になる"
            }
            
            data = {
                "logs": [
                    "=== 現在の状況 ===",
                    "[現在地]",
                    "座標（X=-3.2, Z=-0.6）",
                    "[周辺の状況]",
                    "x方向に+0.0、z方向に+0.0に運搬可能な椅子（座標: x=-3.2, z=-0.6）",
                    "[持っているもの]",
                    "何も持っていません",
                    "[検出情報]",
                    "+X+Z約0.1メートルに運搬可能な椅子あり。pickupコマンドで持ち上げ可能",
                    "[可能なコマンド]",
                    "navigation（任意の座標へ移動）、pickup（運搬可能な椅子を拾う）"
                ]
            }
            
            self.run_test(
                "次ステップ取得",
                data,
                ACTIONS["STEP_RETRIEVED"],
                "キューから次のペンディングステップを取得"
            )
    
    def test_complete_step_and_get_next(self):
        """ステップ完了後次ステップ取得のテスト"""
        with patch('command_controller.step_manager') as mock_step_manager:
            # 実行中ステップありの状態をモック
            mock_step_manager.get_queue_status.return_value = {
                "total_steps": 3,
                "status_counts": {"pending": 1, "executing": 1, "completed": 1, "failed": 0},
                "current_step_id": "step_1",
                "has_pending_steps": True
            }
            
            mock_step_manager.complete_step.return_value = True
            mock_step_manager.get_next_step.return_value = {
                "id": "step_2",
                "command": "navigate",
                "x": 5.5,
                "z": -3.6,
                "reasoning": "ChairArea付近に到達してpickupコマンドが使用可能になる"
            }
            
            data = {
                "step_id": "step_1",
                "logs": [
                    "=== 現在の状況 ===",
                    "[現在地]",
                    "座標（X=-3.2, Z=-0.6）",
                    "[持っているもの]",
                    "運搬可能な椅子",
                    "[実行したアクション]",
                    "運搬可能な椅子を持ち上げました！pickupコマンドで置くことができます。",
                    "[可能なコマンド]",
                    "navigation（任意の座標へ移動）、pickup（床に置く）"
                ]
            }
            
            self.run_test(
                "ステップ完了後次取得",
                data,
                ACTIONS["STEP_COMPLETED_NEXT_RETRIEVED"],
                "現在のステップを完了状態にして次のステップを取得"
            )
    
    def test_task_completion_check(self):
        """タスク完了判定のテスト"""
        with patch('command_controller.step_manager') as mock_step_manager:
            # 全ステップ完了の状態をモック
            mock_step_manager.get_queue_status.return_value = {
                "total_steps": 3,
                "status_counts": {"pending": 0, "executing": 0, "completed": 3, "failed": 0},
                "current_step_id": None,
                "has_pending_steps": False
            }
            
            mock_step_manager.steps = [
                {"task_id": "task_123", "id": "step_1"},
                {"task_id": "task_123", "id": "step_2"},
                {"task_id": "task_123", "id": "step_3"}
            ]
            
            data = {
                "logs": [
                    "=== 現在の状況 ===",
                    "[現在地]",
                    "座標（X=0.0, Z=3.6）",
                    "[周辺の状況]",
                    "x方向に+0.0、z方向に-0.1にPCプレート（座標: x=0.02, z=3.55）",
                    "x方向に+5.5、z方向に-7.3にChairArea（座標: x=5.48, z=-3.69）",
                    "[持っているもの]",
                    "何も持っていません",
                    "[実行したアクション]",
                    "テレビをONにしました！",
                    "運搬可能な椅子を置きました！場所: 座標X:5.5, Z:-3.7、ChairArea付近",
                    "PCを置きました！場所: 座標X:0.0, Z:3.6、DaiArea付近",
                    "[可能なコマンド]",
                    "navigation（任意の座標へ移動）"
                ]
            }
            
            with patch('command_controller.llm_manager') as mock_llm:
                # LLM2の完了判定をモック
                mock_llm.check_completion.return_value = {
                    "action": "proceed",
                    "reasoning": "全てのタスクが正常に完了しました"
                }
                
                # LLM1の新タスク計画をモック
                mock_llm.plan_task.return_value = [
                    {
                        "command": "wait",
                        "reasoning": "次のタスクを計画中"
                    }
                ]
                
                mock_step_manager.add_steps.return_value = ["step_new_1"]
                mock_step_manager.get_next_step.return_value = {
                    "id": "step_new_1",
                    "command": "wait",
                    "reasoning": "次のタスクを計画中"
                }
                
                self.run_test(
                    "タスク完了判定",
                    data,
                    ACTIONS["TASK_COMPLETED_NEW_PLANNED"],
                    "全ステップ完了後、LLM2で完了判定し新タスクを計画"
                )
    
    def test_error_reconstruction(self):
        """エラー再構成のテスト"""
        with patch('command_controller.step_manager') as mock_step_manager:
            mock_step_manager.get_queue_status.return_value = {
                "total_steps": 2,
                "status_counts": {"pending": 1, "executing": 0, "completed": 1, "failed": 0},
                "current_step_id": None,
                "has_pending_steps": True
            }
            
            mock_step_manager.current_step_id = "step_2"
            mock_step_manager.get_step.return_value = {
                "id": "step_2",
                "task_id": "task_123",
                "command": "pickup",
                "reasoning": "椅子を拾う"
            }
            
            data = {
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
                ]
            }
            
            with patch('command_controller.llm_manager') as mock_llm:
                # LLM3の再構成をモック
                mock_llm.reconstruct_task.return_value = {
                    "new_steps": [
                        {
                            "command": "navigate",
                            "x": -3.1,
                            "z": -0.5,
                            "reasoning": "椅子の正確な位置に移動"
                        }
                    ]
                }
                
                mock_step_manager.clear_all_steps.return_value = None
                mock_step_manager.add_steps.return_value = ["step_recon_1"]
                mock_step_manager.get_next_step.return_value = {
                    "id": "step_recon_1",
                    "command": "navigate",
                    "x": -3.1,
                    "z": -0.5,
                    "reasoning": "椅子の正確な位置に移動"
                }
                
                self.run_test(
                    "エラー再構成",
                    data,
                    ACTIONS["RECONSTRUCTED_FROM_ERROR"],
                    "エラーログ検出時、LLM3でタスクを再構成"
                )
    
    def test_invalid_request(self):
        """無効なリクエストのテスト"""
        data = None
        
        self.run_test(
            "無効なリクエスト",
            data,
            "error_response",
            "Noneや空のデータに対するエラーハンドリング"
        )
    
    def test_missing_step_id(self):
        """step_id不足のテスト"""
        with patch('command_controller.step_manager') as mock_step_manager:
            mock_step_manager.get_queue_status.return_value = {
                "total_steps": 2,
                "status_counts": {"pending": 1, "executing": 1, "completed": 0, "failed": 0},
                "current_step_id": "step_1",
                "has_pending_steps": True
            }
            
            # より具体的なモック設定でMagicMock混入を防ぐ
            mock_step_manager.get_step.return_value = None
            mock_step_manager.complete_step.return_value = False
            mock_step_manager.get_next_step.return_value = None
            
            data = {
                "logs": [
                    "=== 現在の状況 ===",
                    "[現在地]",
                    "座標（X=0.1, Z=5.4）",
                    "[実行したアクション]",
                    "移動コマンドが完了しました",
                    "[可能なコマンド]",
                    "navigation（任意の座標へ移動）"
                ]
                # step_idが意図的に欠落
            }
            
            self.run_test(
                "step_ID不足",
                data,
                "error_response",
                "ステップ完了通知でstep_idが不足している場合のエラー"
            )
    
    def run_all_tests(self):
        """全テストの実行"""
        print("🧪 LLM出力テストを開始します...\n")
        
        # 各種モックのパッチ
        with patch('command_controller.storage_manager') as mock_storage:
            mock_storage.process_and_save_logs.return_value = None
            mock_storage.get_log_records.return_value = []
            
            # テスト実行
            self.test_initial_planning()
            self.test_get_next_step()
            self.test_complete_step_and_get_next()
            self.test_task_completion_check()
            self.test_error_reconstruction()
            self.test_invalid_request()
            self.test_missing_step_id()
        
        # 結果サマリー
        self.print_summary()
    
    def print_summary(self):
        """テスト結果のサマリー出力"""
        print("\n" + "="*50)
        print("📊 テスト結果サマリー")
        print("="*50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.get("success", False))
        failed_tests = total_tests - passed_tests
        
        print(f"総テスト数: {total_tests}")
        print(f"成功: {passed_tests} ✅")
        print(f"失敗: {failed_tests} ❌")
        print(f"成功率: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n失敗したテスト:")
            for result in self.test_results:
                if not result.get("success", False):
                    print(f"  - {result['test_name']}")
                    if "error" in result:
                        print(f"    エラー: {result['error']}")

def main():
    """メイン実行関数"""
    print("🚀 Unity Research Lab Backend - LLM出力テスト")
    print("="*60)
    
    tester = LLMOutputTester()
    tester.run_all_tests()
    
    print("\n✨ テスト完了!")

if __name__ == "__main__":
    main()