"""
ステップマネージャー
タスクから生成されたステップの管理とライフサイクルを制御
"""

import json
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class StepManager:
    
    def __init__(self):
        self.steps: List[Dict] = []
        self.current_step_id: Optional[str] = None
    
    # === ステップ追加・作成 ===
    
    def add_steps(self, task_id: str, steps: List[Dict]) -> List[str]:
        step_ids = []
        
        for i, step in enumerate(steps):
            # ステップの基本妥当性チェック
            if not step.get("command"):
                logger.warning(f"Step {i} missing command, skipping")
                continue
                
            step_id = str(uuid.uuid4())
            step_data = {
                "id": step_id,
                "task_id": task_id,
                "order": i,
                "status": StepStatus.PENDING.value,
                "command": step.get("command"),
                "reasoning": step.get("reasoning", ""),
                "x": step.get("x"),
                "y": step.get("y"),
                "z": step.get("z"),
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "error_message": None
            }
            
            self.steps.append(step_data)
            step_ids.append(step_id)
            
        logger.info(f"Added {len(steps)} steps for task {task_id}")
        return step_ids
    
    # === ステップ実行管理 ===
    
    def get_next_step(self) -> Optional[Dict]:
        # PENDING状態のステップを順序順に探す
        pending_steps = [
            step for step in self.steps 
            if step["status"] == StepStatus.PENDING.value
        ]
        
        if not pending_steps:
            return None
            
        # 最も早い順序のステップを選択（タスクID順、その後order順）
        next_step = min(pending_steps, key=lambda x: (x["task_id"], x["order"]))
        
        logger.debug(f"Selected next step from {len(pending_steps)} pending steps")
        
        # ステップを実行中状態に変更
        next_step["status"] = StepStatus.EXECUTING.value
        next_step["started_at"] = datetime.now().isoformat()
        self.current_step_id = next_step["id"]
        
        logger.info(f"Starting step {next_step['id']}: {next_step['command']} - {next_step['reasoning']}")
        return next_step
    
    def complete_step(self, step_id: str) -> bool:
        for step in self.steps:
            if step["id"] == step_id:
                step["status"] = StepStatus.COMPLETED.value
                step["completed_at"] = datetime.now().isoformat()
                
                if self.current_step_id == step_id:
                    self.current_step_id = None
                
                logger.info(f"Completed step {step_id}")
                return True
        
        logger.warning(f"Step {step_id} not found for completion")
        return False
    
    def fail_step(self, step_id: str, error_message: str) -> bool:
        for step in self.steps:
            if step["id"] == step_id:
                step["status"] = StepStatus.FAILED.value
                step["error_message"] = error_message
                step["completed_at"] = datetime.now().isoformat()
                
                if self.current_step_id == step_id:
                    self.current_step_id = None
                
                logger.error(f"Failed step {step_id}: {error_message}")
                return True
        
        logger.warning(f"Step {step_id} not found for failure")
        return False
    
    # === ステップ取得・検索 ===
    
    def get_step(self, step_id: str) -> Optional[Dict]:
        for step in self.steps:
            if step["id"] == step_id:
                return step
        return None
    
    def get_task_steps(self, task_id: str) -> List[Dict]:
        return [step for step in self.steps if step["task_id"] == task_id]
    
    def get_queue_status(self) -> Dict:
        status_counts = {}
        for status in StepStatus:
            status_counts[status.value] = len([
                s for s in self.steps if s["status"] == status.value
            ])
        
        return {
            "total_steps": len(self.steps),
            "status_counts": status_counts,
            "current_step_id": self.current_step_id,
            "has_pending_steps": status_counts[StepStatus.PENDING.value] > 0
        }
    
    # === ステップクリア・管理 ===
    
    def clear_completed_steps(self):
        initial_count = len(self.steps)
        self.steps = [
            step for step in self.steps 
            if step["status"] not in [StepStatus.COMPLETED.value, StepStatus.FAILED.value]
        ]
        cleared_count = initial_count - len(self.steps)
        
        if cleared_count > 0:
            logger.info(f"Cleared {cleared_count} completed/failed steps")
    
    def clear_all_steps(self):
        self.steps.clear()
        self.current_step_id = None
        logger.info("Cleared all steps")


# グローバルステップマネージャーインスタンス
step_manager = StepManager()