#!/usr/bin/env python3
"""
Unity-LLM Backend 統合テストスクリプト
"""

import requests
import json
import time
import sys
import os

class BackendTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
    
    def log_test(self, test_name, success, message=""):
        """テスト結果をログに記録"""
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {test_name}: {message}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message
        })
    
    def test_health_check(self):
        """ヘルスチェックテスト"""
        try:
            response = self.session.get(f"{self.base_url}/api/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_test("Health Check", True, "Backend is healthy")
                    return True
                else:
                    self.log_test("Health Check", False, f"Unexpected status: {data.get('status')}")
                    return False
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_test("Health Check", False, f"Connection error: {str(e)}")
            return False
    
    def test_process_logs(self):
        """ログ処理テスト"""
        test_logs = [
            "[Narrator] === 現在の状況 ===",
            "[現在地]",
            "  座標（X=0.0, Z=0.0）",
            "  +Z方向を向いています",
            "[周辺の状況]",
            "  +X約2.5メートルにテレビ",
            "  -X約3.0メートルにPC", 
            "[持っているもの]",
            "  何も持っていません",
            "[可能なコマンド]",
            "  +Z、+X、-Z、-X",
            "========================"
        ]
        
        try:
            payload = {"logs": test_logs}
            response = self.session.post(
                f"{self.base_url}/api/process_logs",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["command", "reasoning", "current_task", "progress", "task_status", "timestamp"]
                if all(field in data for field in required_fields):
                    command = data["command"]
                    reasoning = data["reasoning"]
                    current_task = data["current_task"]
                    progress = data["progress"]
                    self.log_test("Process Logs", True, f"Command: {command}, Task: {current_task}, Progress: {progress}")
                    return True
                else:
                    missing_fields = [field for field in required_fields if field not in data]
                    self.log_test("Process Logs", False, f"Missing fields in response: {missing_fields}")
                    return False
            else:
                self.log_test("Process Logs", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_test("Process Logs", False, f"Request error: {str(e)}")
            return False
    
    def test_llm_connection(self):
        """LLM接続テスト"""
        try:
            payload = {"message": "This is a test message for LLM connection."}
            response = self.session.post(
                f"{self.base_url}/api/test_llm",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if "response" in data and "timestamp" in data:
                    self.log_test("LLM Connection", True, f"LLM responded: {data['response'][:50]}...")
                    return True
                else:
                    self.log_test("LLM Connection", False, f"LLM test failed: {data}")
                    return False
            else:
                self.log_test("LLM Connection", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_test("LLM Connection", False, f"Request error: {str(e)}")
            return False
    
    def test_invalid_request(self):
        """無効なリクエストのテスト"""
        try:
            # 無効なペイロード
            response = self.session.post(
                f"{self.base_url}/api/process_logs",
                json={"invalid": "data"},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 400:
                self.log_test("Invalid Request", True, "Correctly rejected invalid request")
                return True
            else:
                self.log_test("Invalid Request", False, f"Expected 400, got {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_test("Invalid Request", False, f"Request error: {str(e)}")
            return False
    
    def test_task_status_api(self):
        """タスク状況API テスト"""
        try:
            response = self.session.get(f"{self.base_url}/api/task_status", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["dependencies", "task_dag", "task_details", "timestamp"]
                if all(field in data for field in required_fields):
                    self.log_test("Task Status API", True, f"Retrieved task configuration successfully")
                    return True
                else:
                    missing_fields = [field for field in required_fields if field not in data]
                    self.log_test("Task Status API", False, f"Missing fields: {missing_fields}")
                    return False
            else:
                self.log_test("Task Status API", False, f"HTTP {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_test("Task Status API", False, f"Request error: {str(e)}")
            return False
    
    def test_log_statistics_api(self):
        """ログ統計API テスト"""
        try:
            response = self.session.get(f"{self.base_url}/api/logs/statistics", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["total_entries", "commands", "tasks"]
                if all(field in data for field in required_fields):
                    self.log_test("Log Statistics API", True, f"Retrieved log statistics successfully")
                    return True
                else:
                    missing_fields = [field for field in required_fields if field not in data]
                    self.log_test("Log Statistics API", False, f"Missing fields: {missing_fields}")
                    return False
            else:
                self.log_test("Log Statistics API", False, f"HTTP {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_test("Log Statistics API", False, f"Request error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """すべてのテストを実行"""
        print("=" * 50)
        print("Unity-LLM Backend Integration Tests")
        print("=" * 50)
        
        # OpenAI API Key のチェック
        if not os.environ.get('OPENAI_API_KEY'):
            print("WARNING: OPENAI_API_KEY environment variable not set")
            print("Some tests may fail without a valid API key")
        
        tests = [
            self.test_health_check,
            self.test_invalid_request,
            self.test_llm_connection,
            self.test_process_logs,
            self.test_task_status_api,
            self.test_log_statistics_api,
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed += 1
                time.sleep(1)  # テスト間の間隔
            except Exception as e:
                self.log_test(test.__name__, False, f"Test execution error: {str(e)}")
        
        print("\n" + "=" * 50)
        print(f"Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("✓ All tests passed!")
            return True
        else:
            print(f"✗ {total - passed} test(s) failed")
            return False
    
    def wait_for_backend(self, max_wait=60):
        """バックエンドが起動するまで待機"""
        print(f"Waiting for backend at {self.base_url}...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                response = self.session.get(f"{self.base_url}/api/health", timeout=5)
                if response.status_code == 200:
                    print("Backend is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(2)
        
        print(f"Backend did not respond within {max_wait} seconds")
        return False

def main():
    """メイン関数"""
    # コマンドライン引数の処理
    backend_url = "http://localhost:5000"
    if len(sys.argv) > 1:
        backend_url = sys.argv[1]
    
    tester = BackendTester(backend_url)
    
    # バックエンドの起動を待機
    if not tester.wait_for_backend():
        print("ERROR: Could not connect to backend")
        sys.exit(1)
    
    # テストを実行
    success = tester.run_all_tests()
    
    # 結果に応じて終了
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 