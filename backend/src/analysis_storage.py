"""
分析結果ストレージシステム
AIエージェントの分析結果と状態を永続化・管理する
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class AnalysisStorage:
    def __init__(self, storage_dir: str = "storage"):
        """
        分析結果ストレージの初期化
        
        Args:
            storage_dir: ストレージディレクトリのパス
        """
        self.storage_dir = storage_dir
        self.analysis_file = os.path.join(storage_dir, "analysis_history.json")
        self.current_state_file = os.path.join(storage_dir, "current_state.json")
        
        # ストレージディレクトリを作成
        os.makedirs(storage_dir, exist_ok=True)
        
        # ファイルが存在しない場合は初期化
        self._initialize_files()
    
    def _initialize_files(self):
        """ストレージファイルを初期化"""
        if not os.path.exists(self.analysis_file):
            with open(self.analysis_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        
        if not os.path.exists(self.current_state_file):
            initial_state = {
                "last_updated": datetime.now().isoformat(),
                "current_task": None,
                "task_progress": {},
                "player_state": {},
                "environment_state": {}
            }
            with open(self.current_state_file, 'w', encoding='utf-8') as f:
                json.dump(initial_state, f, ensure_ascii=False, indent=2)
    
    def save_analysis(self, analysis_data: Dict) -> bool:
        """
        分析結果を保存
        
        Args:
            analysis_data: 保存する分析データ
            
        Returns:
            bool: 保存成功かどうか
        """
        try:
            # タイムスタンプを追加
            analysis_data["timestamp"] = datetime.now().isoformat()
            analysis_data["analysis_id"] = self._generate_analysis_id()
            
            # 既存のデータを読み込み
            with open(self.analysis_file, 'r', encoding='utf-8') as f:
                analyses = json.load(f)
            
            # 新しい分析結果を追加
            analyses.append(analysis_data)
            
            # 最新の100件のみ保持
            if len(analyses) > 100:
                analyses = analyses[-100:]
            
            # ファイルに保存
            with open(self.analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analyses, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Analysis saved with ID: {analysis_data['analysis_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save analysis: {str(e)}")
            return False
    
    def get_recent_analyses(self, limit: int = 10) -> List[Dict]:
        """
        最近の分析結果を取得
        
        Args:
            limit: 取得する分析結果の件数
            
        Returns:
            List[Dict]: 分析結果のリスト
        """
        try:
            with open(self.analysis_file, 'r', encoding='utf-8') as f:
                analyses = json.load(f)
            
            # 最新のlimit件を返す
            return analyses[-limit:] if len(analyses) > limit else analyses
            
        except Exception as e:
            logger.error(f"Failed to get recent analyses: {str(e)}")
            return []
    
    def get_analyses_by_task(self, task_id: str) -> List[Dict]:
        """
        特定のタスクに関連する分析結果を取得
        
        Args:
            task_id: タスクID
            
        Returns:
            List[Dict]: 該当する分析結果のリスト
        """
        try:
            with open(self.analysis_file, 'r', encoding='utf-8') as f:
                analyses = json.load(f)
            
            # 指定されたタスクに関連する分析結果をフィルタ
            task_analyses = [
                analysis for analysis in analyses 
                if analysis.get("current_task") == task_id
            ]
            
            return task_analyses
            
        except Exception as e:
            logger.error(f"Failed to get analyses by task: {str(e)}")
            return []
    
    def save_current_state(self, state_data: Dict) -> bool:
        """
        現在の状態を保存
        
        Args:
            state_data: 保存する状態データ
            
        Returns:
            bool: 保存成功かどうか
        """
        try:
            # タイムスタンプを更新
            state_data["last_updated"] = datetime.now().isoformat()
            
            # ファイルに保存
            with open(self.current_state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
            
            logger.info("Current state saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save current state: {str(e)}")
            return False
    
    def get_current_state(self) -> Dict:
        """
        現在の状態を取得
        
        Returns:
            Dict: 現在の状態データ
        """
        try:
            with open(self.current_state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            return state
            
        except Exception as e:
            logger.error(f"Failed to get current state: {str(e)}")
            return {}
    
    def _generate_analysis_id(self) -> str:
        """分析IDを生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"analysis_{timestamp}"
    
    def get_analysis_summary(self) -> Dict:
        """
        分析結果のサマリーを取得
        
        Returns:
            Dict: 分析サマリー
        """
        try:
            with open(self.analysis_file, 'r', encoding='utf-8') as f:
                analyses = json.load(f)
            
            total_analyses = len(analyses)
            recent_analyses = analyses[-10:] if len(analyses) > 10 else analyses
            
            # タスク別の分析回数を集計
            task_counts = {}
            for analysis in analyses:
                task = analysis.get("current_task", "unknown")
                task_counts[task] = task_counts.get(task, 0) + 1
            
            return {
                "total_analyses": total_analyses,
                "recent_analyses_count": len(recent_analyses),
                "task_analysis_counts": task_counts,
                "last_analysis_time": analyses[-1].get("timestamp") if analyses else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get analysis summary: {str(e)}")
            return {}

# グローバルストレージインスタンス
storage = AnalysisStorage() 