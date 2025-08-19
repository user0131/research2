# 研究室タスク管理システム

# 最終的な目標
GOAL = "研究室の準備：テレビをONにし、椅子とPCプレートを適切な場所に移動し、PCをプレート上に配置する"

# 行うべきタスク
TASKS = {
    "tv_switch": "テレビの電源をONにする",
    "chair_move": "椅子をChairAreaに移動する", 
    "pc_plate_move": "PCプレートをDaiAreaに移動する",
    "put_pc_on_plate": "PCをプレート上に配置する"
}

# 依存関係（DAG）
DEPENDENCIES = {
    "tv_switch": [],  # 依存なし（いつでも実行可能）
    "chair_move": [],  # 依存なし（いつでも実行可能）
    "pc_plate_move": [],  # 依存なし（いつでも実行可能）
    "put_pc_on_plate": ["pc_plate_move"],  # PC Plate Moveの完了が必要（プレートが配置されてから）
    "finish": ["tv_switch", "chair_move", "put_pc_on_plate"]  # TV switch、Chair Move、Put PC on Plateの全てが完了
}

# タスク実行例（Few-shot prompting用）
TASK_EXAMPLES = {
    "tv_switch": {
        "description": "テレビの電源をONにする",
        "steps": [
            "navigate: テレビの位置（X=0.0, Z=10.2）に移動する",
            "interact: テレビの電源をONにする"
        ],
        "example_command_sequence": [
            {
                "command": "navigate",
                "x": 0.1,
                "y": 0.0,
                "z": 5.4,
                "reasoning": "テレビに隣接してinteractコマンドが使用可能になる"
            },
            {
                "command": "interact",
                "reasoning": "テレビが点灯し操作完了メッセージが表示される"
            }
        ]
    },
    
    "chair_move": {
        "description": "椅子をChairAreaに移動する",
        "steps": [
            "navigate: 椅子の位置（X=-3.2, Z=-0.6）に移動する",
            "pickup: 椅子を拾う",
            "navigate: ChairArea（X=5.48, Z=-3.69）に移動する",
            "pickup: 椅子を置く"
        ],
        "example_command_sequence": [
            {
                "command": "navigate",
                "x": -3.1,
                "y": 0.0,
                "z": -0.5,
                "reasoning": "椅子に隣接してpickupコマンドが使用可能になる"
            },
            {
                "command": "pickup",
                "reasoning": "椅子を持っている状態になる"
            },
            {
                "command": "navigate",
                "x": 5.5,
                "y": 0.0,
                "z": -3.6,
                "reasoning": "ChairArea付近に到達してpickupコマンドが使用可能になる"
            },
            {
                "command": "pickup",
                "reasoning": "椅子がChairAreaに配置され手から離れる"
            }
        ]
    },
    
    "pc_plate_move": {
        "description": "PCプレートをDaiAreaに移動する",
        "steps": [
            "navigate: PCプレートの位置（X=4.3, Z=8.4）に移動する",
            "pickup: PCプレートを拾う",
            "navigate: DaiArea（X=0.02, Z=3.55）に移動する",
            "pickup: PCプレートを置く"
        ],
        "example_command_sequence": [
            {
                "command": "navigate",
                "x": 4.4,
                "y": 0.0,
                "z": 8.5,
                "reasoning": "PCプレートに隣接してpickupコマンドが使用可能になる"
            },
            {
                "command": "pickup",
                "reasoning": "PCプレートを持っている状態になる"
            },
            {
                "command": "navigate",
                "x": 0.1,
                "y": 0.0,
                "z": 3.6,
                "reasoning": "DaiArea付近に到達してpickupコマンドが使用可能になる"
            },
            {
                "command": "pickup",
                "reasoning": "PCプレートがDaiAreaに配置され手から離れる"
            }
        ]
    },
    
    "put_pc_on_plate": {
        "description": "PCをプレート上に配置する",
        "steps": [
            "navigate: PCの位置（X=3.0, Z=1.5）に移動する",
            "pickup: PCを拾う",
            "navigate: DaiAreaのPCプレート上に移動する",
            "pickup: PCを置く"
        ],
        "example_command_sequence": [
            {
                "command": "navigate",
                "x": 3.1,
                "y": 0.0,
                "z": 1.6,
                "reasoning": "PCに隣接してpickupコマンドが使用可能になる"
            },
            {
                "command": "pickup",
                "reasoning": "PCを持っている状態になる"
            },
            {
                "command": "navigate",
                "x": 0.1,
                "y": 0.0,
                "z": 3.6,
                "reasoning": "PCプレートの上に到達してpickupコマンドが使用可能になる"
            },
            {
                "command": "pickup",
                "reasoning": "PCがプレートの上に配置され手から離れる"
            }
        ]
    }
}

def get_goal():
    """最終的な目標を取得"""
    return GOAL

def get_tasks():
    """行うべきタスクを取得"""
    return TASKS

def get_dependencies():
    """依存関係を取得"""
    return DEPENDENCIES

def get_task_description(task_id):
    """特定のタスクの説明を取得"""
    return TASKS.get(task_id, "未知のタスク")

def get_task_dependencies(task_id):
    """特定のタスクの依存関係を取得"""
    return DEPENDENCIES.get(task_id, [])

def get_task_examples():
    """タスク実行例を取得"""
    return TASK_EXAMPLES

def get_task_example(task_id):
    """特定のタスクの実行例を取得"""
    return TASK_EXAMPLES.get(task_id, {"description": "未知のタスク", "steps": [], "example_sequence": [], "completion_criteria": "不明"})