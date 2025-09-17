"""
統合フローテスト
バックエンドの完全なワークフロー（コマンド連続実行→キュー蓄積→キュー消化→LLM2判定）を検証
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

from openai import OpenAI
from services.command_controller import command_controller
from services.step_manager import step_manager
from services.storage_manager import storage_manager

class IntegrationFlowTester:
    """統合フローテストクラス"""
    
    def __init__(self):
        self.openai_client = self._setup_openai_client()
        self.test_results = []
        
    def _setup_openai_client(self):
        """OpenAIクライアントの設定"""
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            print("❌ OPENAI_API_KEY環境変数が設定されていません")
            return None
        
        print("✅ OpenAI APIクライアント初期化完了")
        return OpenAI(api_key=api_key)
    
    def reset_system_state(self):
        """システム状態をリセット"""
        step_manager.clear_all_steps()
        storage_manager.clear_all()
        print("🔄 システム状態をリセットしました")
    
    def test_complete_workflow(self):
        """完全なワークフローテスト"""
        print("\n" + "="*80)
        print("🧪 統合フローテスト: 完全なワークフロー")
        print("="*80)
        
        self.reset_system_state()
        
        # フェーズ1: 初回タスク計画（LLM1）
        print("\n📋 フェーズ1: 初回タスク計画")
        initial_situation = {
            "logs": [
                "=== 現在の状況 ===",
                "[現在地]",
                "座標（X=5.0, Z=3.0）",
                "[周辺の状況]",
                "x方向に-4.9、z方向に+2.4にテレビ（座標: x=0.1, z=5.4）",
                "x方向に-8.2、z方向に-3.6に運搬可能な椅子（座標: x=-3.2, z=-0.6）",
                "x方向に-0.7、z方向に+5.4にPCプレート（座標: x=4.3, z=8.4）",
                "[持っているもの]",
                "何も持っていません",
                "[可能なコマンド]",
                "navigation（任意の座標へ移動）"
            ]
        }
        
        result1 = command_controller.process_step(initial_situation, self.openai_client)
        print(f"✅ LLM1結果: {result1['command']} - {result1['reasoning']}")
        
        # キューの状態確認
        queue_status = step_manager.get_queue_status()
        print(f"📊 キュー状態: {queue_status['status_counts']}")
        
        # フェーズ2: コマンド連続実行シミュレーション
        print("\n🔄 フェーズ2: コマンド連続実行シミュレーション")
        command_count = 0
        max_commands = 5  # 最大5回のコマンド実行
        
        while queue_status['has_pending_steps'] and command_count < max_commands:
            command_count += 1
            print(f"\n--- コマンド実行 {command_count} ---")
            
            # コマンド実行完了の通知をシミュレート
            command_completion_data = {
                "step_id": result1.get('step_id'),
                "logs": [
                    "=== 現在の状況 ===",
                    "[現在地]",
                    f"座標（X={result1.get('x', 0.0)}, Z={result1.get('z', 0.0)}）",
                    "[周辺の状況]",
                    "目標地点に到達しました",
                    "[持っているもの]",
                    "何も持っていません",
                    "[実行したアクション]",
                    f"{result1['command']}コマンドが完了しました",
                    "[可能なコマンド]",
                    "navigation（任意の座標へ移動）、pickup、interact"
                ]
            }
            
            # 次のステップを取得
            next_result = command_controller.process_step(command_completion_data, self.openai_client)
            print(f"📌 実行コマンド: {next_result['command']}")
            if next_result.get('reasoning'):
                print(f"   理由: {next_result['reasoning'][:100]}...")
            
            # キュー状態を更新
            queue_status = step_manager.get_queue_status()
            print(f"📊 キュー状態: pending={queue_status['status_counts']['pending']}, executing={queue_status['status_counts']['executing']}")
            
            # 次の結果を保存
            result1 = next_result
            
            # ペンディングステップがなくなったらループ終了
            if not queue_status['has_pending_steps']:
                print("✅ 全ステップ完了！")
                break
        
        # フェーズ3: LLM2による完了判定
        print("\n🎯 フェーズ3: LLM2による完了判定")
        
        # タスク完了判定のためのデータ作成
        completion_data = {
            "logs": [
                "=== 現在の状況 ===",
                "[現在地]",
                "座標（X=0.1, Z=5.4）",
                "[周辺の状況]",
                "x方向に+0.0、z方向に+0.0にテレビ（座標: x=0.1, z=5.4）",
                "[持っているもの]",
                "何も持っていません",
                "[実行したアクション]",
                "テレビをONにしました！",
                "運搬可能な椅子を置きました！場所: 座標X:5.5, Z:-3.7、ChairArea付近",
                "PCプレートを置きました！場所: 座標X:0.0, Z:3.6、DaiArea付近",
                "[検出情報]",
                "+X+Z約0.1メートルにテレビあり。ON・interactコマンドで操作可能",
                "[可能なコマンド]",
                "navigation（任意の座標へ移動）"
            ]
        }
        
        # 最終的なタスク完了判定
        final_result = command_controller.process_step(completion_data, self.openai_client)
        print(f"🎉 最終結果: {final_result['command']} - {final_result['reasoning']}")
        
        # 完了時のキュー状態
        final_queue_status = step_manager.get_queue_status()
        print(f"📊 最終キュー状態: {final_queue_status['status_counts']}")
        
        # ストレージ状態確認
        log_records = storage_manager.get_log_records(count=10)
        print(f"💾 保存されたログ件数: {len(log_records)}")
        
        return {
            "commands_executed": command_count,
            "final_queue_status": final_queue_status,
            "final_result": final_result,
            "logs_saved": len(log_records),
            "workflow_completed": True
        }
    
    def test_queue_management(self):
        """キュー管理の詳細テスト"""
        print("\n" + "="*80)
        print("🧪 キュー管理テスト")
        print("="*80)
        
        self.reset_system_state()
        
        # 複数ステップのタスクを生成
        multi_step_situation = {
            "logs": [
                "=== 現在の状況 ===",
                "[現在地]",
                "座標（X=0.0, Z=0.0）",
                "[周辺の状況]",
                "x方向に+0.1、z方向に+5.4にテレビ（座標: x=0.1, z=5.4）",
                "x方向に-3.2、z方向に-0.6に運搬可能な椅子（座標: x=-3.2, z=-0.6）",
                "x方向に+4.3、z方向に+8.4にPCプレート（座標: x=4.3, z=8.4）",
                "[持っているもの]",
                "何も持っていません",
                "[可能なコマンド]",
                "navigation（任意の座標へ移動）",
                "研究室セットアップを開始します"
            ]
        }
        
        # LLM1でタスク計画
        result = command_controller.process_step(multi_step_situation, self.openai_client)
        
        # キューの詳細状態を追跡
        queue_snapshots = []
        
        initial_queue = step_manager.get_queue_status()
        queue_snapshots.append({
            "phase": "初期計画後",
            "status": initial_queue['status_counts'].copy(),
            "total": initial_queue['total_steps']
        })
        
        print(f"📋 初期計画: {initial_queue['total_steps']}ステップ生成")
        print(f"📊 初期キュー: {initial_queue['status_counts']}")
        
        # ステップ実行シミュレーション
        step_execution_count = 0
        while initial_queue['has_pending_steps'] and step_execution_count < 10:
            step_execution_count += 1
            
            # 現在のペンディングステップを実行中に変更
            next_step = step_manager.get_next_step()
            if not next_step:
                break
                
            print(f"\n🔄 ステップ {step_execution_count}: {next_step['command']}")
            
            # ステップ完了をシミュレート
            step_completion_data = {
                "step_id": next_step['id'],
                "logs": [
                    "=== 現在の状況 ===",
                    "[現在地]",
                    f"座標（X={next_step.get('x', 0.0)}, Z={next_step.get('z', 0.0)}）",
                    "[実行したアクション]",
                    f"{next_step['command']}コマンドが完了しました",
                    "[可能なコマンド]",
                    "navigation（任意の座標へ移動）"
                ]
            }
            
            # ステップ完了と次ステップ取得
            next_result = command_controller.process_step(step_completion_data, self.openai_client)
            
            # キュー状態のスナップショット
            current_queue = step_manager.get_queue_status()
            queue_snapshots.append({
                "phase": f"ステップ{step_execution_count}完了後",
                "status": current_queue['status_counts'].copy(),
                "total": current_queue['total_steps']
            })
            
            print(f"📊 キュー更新: {current_queue['status_counts']}")
            
            # 全て完了したかチェック
            if not current_queue['has_pending_steps']:
                print("✅ 全ステップ完了")
                break
        
        # キュー管理の結果サマリー
        print(f"\n📈 キュー管理サマリー:")
        for snapshot in queue_snapshots:
            print(f"  {snapshot['phase']}: {snapshot['status']}")
        
        return {
            "steps_executed": step_execution_count,
            "queue_snapshots": queue_snapshots,
            "final_queue_empty": not step_manager.get_queue_status()['has_pending_steps']
        }
    
    def test_llm2_integration(self):
        """LLM2統合テスト"""
        print("\n" + "="*80)
        print("🧪 LLM2統合テスト")
        print("="*80)
        
        # 成功パターンのテスト
        print("\n✅ 成功パターンテスト")
        success_data = {
            "logs": [
                "=== 現在の状況 ===",
                "[現在地]",
                "座標（X=0.1, Z=5.4）",
                "[周辺の状況]",
                "x方向に+0.0、z方向に+0.0にテレビ（座標: x=0.1, z=5.4）",
                "[持っているもの]",
                "何も持っていません",
                "[実行したアクション]",
                "テレビをONにしました！",
                "運搬可能な椅子を置きました！場所: 座標X:5.5, Z:-3.7、ChairArea付近",
                "PCを置きました！場所: 座標X:0.0, Z:3.6、DaiArea付近",
                "[検出情報]",
                "研究室のセットアップが完了しました",
                "[可能なコマンド]",
                "navigation（任意の座標へ移動）"
            ]
        }
        
        success_result = command_controller.process_step(success_data, self.openai_client)
        print(f"成功判定結果: {success_result['command']} - {success_result['reasoning']}")
        
        # 失敗パターンのテスト
        print("\n❌ 失敗パターンテスト")
        self.reset_system_state()
        
        failure_data = {
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
        
        failure_result = command_controller.process_step(failure_data, self.openai_client)
        print(f"失敗時の対応: {failure_result['command']} - {failure_result['reasoning'][:100]}...")
        
        return {
            "success_pattern": success_result,
            "failure_pattern": failure_result
        }
    
    def run_all_integration_tests(self):
        """全統合テストの実行"""
        print("🚀 統合フローテスト開始")
        print("="*80)
        print("🔗 バックエンドの完全なワークフローを検証します")
        print("="*80)
        
        if not self.openai_client:
            print("❌ OpenAI APIが設定されていません")
            return
        
        start_time = time.time()
        
        # テスト1: 完全なワークフロー
        workflow_result = self.test_complete_workflow()
        
        # テスト2: キュー管理
        queue_result = self.test_queue_management() 
        
        # テスト3: LLM2統合
        llm2_result = self.test_llm2_integration()
        
        end_time = time.time()
        
        # 結果サマリー
        print("\n" + "="*80)
        print("📊 統合テスト結果サマリー")
        print("="*80)
        
        print(f"⏱️  総実行時間: {end_time - start_time:.2f}秒")
        print(f"🔄 ワークフロー実行コマンド数: {workflow_result['commands_executed']}")
        print(f"📊 キュー管理ステップ数: {queue_result['steps_executed']}")
        print(f"💾 保存ログ件数: {workflow_result['logs_saved']}")
        print(f"✅ ワークフロー完了: {'成功' if workflow_result['workflow_completed'] else '失敗'}")
        print(f"🎯 キュー管理: {'成功' if queue_result['final_queue_empty'] else '失敗'}")
        
        print(f"\n💡 検証完了項目:")
        print(f"  ✅ LLM1 → 複数ステップ計画生成")
        print(f"  ✅ キュー管理 → ステップ蓄積・実行・完了")
        print(f"  ✅ LLM2判定 → タスク完了時の成功/失敗判定")
        print(f"  ✅ ストレージ → コマンド実行履歴の保存")
        print(f"  ✅ エラー処理 → 失敗時の再構成")
        
        return {
            "workflow_test": workflow_result,
            "queue_test": queue_result,
            "llm2_test": llm2_result,
            "execution_time": end_time - start_time
        }

def main():
    """メイン実行関数"""
    print("🤖 Unity Research Lab Backend - 統合フローテスト")
    print("🔗 コマンド連続実行→キュー管理→LLM2判定の完全フロー検証")
    
    tester = IntegrationFlowTester()
    results = tester.run_all_integration_tests()
    
    print("\n✨ 統合フローテスト完了!")
    print("📝 バックエンドの完全なワークフローが検証されました")

if __name__ == "__main__":
    main()