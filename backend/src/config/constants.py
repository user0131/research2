"""
研究室タスク管理システム定数
研究室環境での自動化タスクに関する定数・設定値を管理
"""

# ======================================================================
# システム目標とタスク定義
# ======================================================================

GOAL = "研究室の準備：テレビをONにし、椅子とPCプレートを適切な場所に移動し、PCをプレート上に配置する"

TASKS = {
    "tv_switch": "テレビの電源をONにする",
    "chair_move": "椅子をChairAreaに移動する", 
    "pc_plate_move": "PCプレートをDaiAreaに移動する",
    "put_pc_on_plate": "PCをプレート上に配置する"
}

DEPENDENCIES = {
    "tv_switch": [],
    "chair_move": [],
    "pc_plate_move": [],
    "put_pc_on_plate": ["pc_plate_move"],
    "finish": ["tv_switch", "chair_move", "put_pc_on_plate"]
}

# ======================================================================
# 利用可能なコマンド定義
# ======================================================================

AVAILABLE_COMMANDS = {
    "navigate": {
        "description": "指定座標への移動",
        "parameters": ["x", "y", "z"],
        "usage": "navigate: 座標(x, y, z)を指定してその位置に移動する"
    },
    "pickup": {
        "description": "アイテムの拾い上げ/設置",
        "parameters": [],
        "usage": "pickup: アイテムに隣接している場合、拾い上げる。アイテムを持っている場合、設置する"
    },
    "interact": {
        "description": "オブジェクトとの相互作用",
        "parameters": [],
        "usage": "interact: テレビなどのオブジェクトに隣接している場合、相互作用する（電源ON/OFFなど）"
    },
    "wait": {
        "description": "待機",
        "parameters": [],
        "usage": "wait: 何もせずに待機する"
    }
}

# ======================================================================
# LLMプロンプトテンプレート
# ======================================================================

PROMPT_TEMPLATES = {
    "available_commands": """
## 利用可能なコマンド
- "navigate(x,z)": 指定座標への移動 (例: navigate(0.1,5.4))
- "pickup": アイテムの拾い上げ/設置
- "interact": オブジェクトとの相互作用
- "wait": 待機""",
    
    "step_format_example": """
## ステップ出力形式
[
    {
        "command": "navigate(x,z)",
        "reasoning": "このステップで達成すべき具体的な目標"
    },
    {
        "command": "pickup",
        "reasoning": "pickup実行で達成すべき具体的な目標"
    },
    {
        "command": "interact",
        "reasoning": "interact実行で達成すべき具体的な目標"
    }
]""",
    
    "completion_check_criteria": """
## 判断基準
ステップのreasoningフィールドに記載された達成条件がログから確認できるかを判定してください。

### 判断結果:
- **proceed**: reasoningが達成された
- **rebuild**: reasoningが達成されていない""",
    
    "json_output_format": """
## 出力形式
{
    "action": "proceed" または "rebuild",
    "reasoning": "判断の理由の詳細説明"
}""",
    
    "reconstruction_output_format": """
## 出力形式
{
    "new_steps": [
        {
            "command": "navigate(x,z)",
            "reasoning": "このステップで達成すべき具体的な目標"
        }
    ]
}""",
    
    "error_fallback_step": {
        "command": "wait",
        "reasoning": "システムエラーのため待機"
    }
}

# ======================================================================
# タスク実行例（Few-shot Prompting用）
# ======================================================================
TASK_EXAMPLES = {
    "tv_switch": {
        "description": "テレビの電源をONにする",
        "steps": [
            "navigate: テレビの位置（X=0.0, Z=10.2）に移動する",
            "interact: テレビの電源をONにする"
        ],
        "example_command_sequence": [
            {
                "command": "navigate(0.1,5.4)",
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
                "command": "navigate(-3.1,-0.5)",
                "reasoning": "椅子に隣接してpickupコマンドが使用可能になる"
            },
            {
                "command": "pickup",
                "reasoning": "椅子を持っている状態になる"
            },
            {
                "command": "navigate(5.5,-3.6)",
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
                "command": "navigate(4.4,8.5)",
                "reasoning": "PCプレートに隣接してpickupコマンドが使用可能になる"
            },
            {
                "command": "pickup",
                "reasoning": "PCプレートを持っている状態になる"
            },
            {
                "command": "navigate(0.1,3.6)",
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
                "command": "navigate(3.1,1.6)",
                "reasoning": "PCに隣接してpickupコマンドが使用可能になる"
            },
            {
                "command": "pickup",
                "reasoning": "PCを持っている状態になる"
            },
            {
                "command": "navigate(0.1,3.6)",
                "reasoning": "PCプレートの上に到達してpickupコマンドが使用可能になる"
            },
            {
                "command": "pickup",
                "reasoning": "PCがプレートの上に配置され手から離れる"
            }
        ]
    }
}

# ======================================================================
# アクセサー関数
# ======================================================================

def get_goal():
    return GOAL

def get_tasks():
    return TASKS

def get_dependencies():
    return DEPENDENCIES

def get_task_description(task_id):
    return TASKS.get(task_id, "未知のタスク")

def get_task_dependencies(task_id):
    return DEPENDENCIES.get(task_id, [])

def get_task_examples():
    return TASK_EXAMPLES

def get_task_example(task_id):
    return TASK_EXAMPLES.get(task_id, {"description": "未知のタスク", "steps": [], "example_command_sequence": []})

def get_available_commands():
    return AVAILABLE_COMMANDS

def get_command_info(command_name):
    return AVAILABLE_COMMANDS.get(command_name, {"description": "未知のコマンド", "parameters": [], "usage": "使用方法不明"})

def get_prompt_templates():
    return PROMPT_TEMPLATES

def get_prompt_template(template_name):
    return PROMPT_TEMPLATES.get(template_name, "")

# ======================================================================
# ベクトルデータベース設定
# ======================================================================

VECTOR_DB_PATH = "./src/data/vector_db"
HIRAKATA_JISIN_VECTOR = "hirakata_jisin_vector"

# ======================================================================
# システム定数
# ======================================================================

# アクション名
ACTIONS = {
    "RECONSTRUCT_ERROR": "reconstruct_error",
    "PLAN_INITIAL": "plan_initial", 
    "GET_NEXT": "get_next",
    "COMPLETE_STEP_AND_GET_NEXT": "complete_step_and_get_next",
    "CHECK_TASK_COMPLETION": "check_task_completion",
    "STEP_RETRIEVED": "step_retrieved",
    "PLANNED": "planned",
    "RECONSTRUCTED_FROM_ERROR": "reconstructed_from_error",
    "TASK_COMPLETED_NEW_PLANNED": "task_completed_new_planned",
    "COMPLETION_STEPS_RECONSTRUCTED": "completion_steps_reconstructed",
    "STEP_COMPLETED_NEXT_RETRIEVED": "step_completed_next_retrieved",
    "NO_STEPS": "no_steps"
}

# エラーメッセージ
ERROR_MESSAGES = {
    "INVALID_REQUEST": "無効なリクエスト形式",
    "MISSING_STEP_ID": "step_idが指定されていません",
    "STEP_COMPLETION_ERROR": "ステップ完了処理中にエラーが発生",
    "TASK_COMPLETION_CHECK_ERROR": "タスク完了判定中にエラーが発生",
    "CURRENT_TASK_ID_ERROR": "現在のタスクID取得中にエラーが発生",
    "TASK_EXECUTION_HISTORY_ERROR": "タスク実行履歴取得中にエラーが発生"
}