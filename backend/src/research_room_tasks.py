# 改善されたタスク構造 - より細かいステップに分解
dependencies = {
    # Step1: テレビのスイッチを操作する（そのまま）
    "step1_tv_operate": [],
    
    # Step2: 椅子をChairAreaに移動する - 4つのサブステップに分解
    "step2a_chair_approach": ["step1_tv_operate"],          # テレビ操作完了後に椅子に近づく
    "step2b_chair_pickup": ["step2a_chair_approach"],       # 椅子を拾う
    "step2c_chair_move_to_area": ["step2b_chair_pickup"],   # 椅子を持ってChairAreaに移動
    "step2d_chair_place": ["step2c_chair_move_to_area"],    # 椅子をChairAreaに置く
    
    # Step3: PCプレートをDaiAreaに移動する - 4つのサブステップに分解
    "step3a_plate_approach": ["step2d_chair_place"],        # 椅子設置完了後にPCプレートに近づく
    "step3b_plate_pickup": ["step3a_plate_approach"],       # PCプレートを拾う
    "step3c_plate_move_to_area": ["step3b_plate_pickup"],   # PCプレートを持ってDaiAreaに移動
    "step3d_plate_place": ["step3c_plate_move_to_area"],    # PCプレートをDaiAreaに置く
    
    # Step4: PCをプレートの上に置く - 4つのサブステップに分解
    "step4a_pc_approach": ["step3d_plate_place"],           # PCに近づく（プレート設置後）
    "step4b_pc_pickup": ["step4a_pc_approach"],             # PCを拾う
    "step4c_pc_move_to_plate": ["step4b_pc_pickup"],        # PCを持ってプレートの上に移動
    "step4d_pc_place": ["step4c_pc_move_to_plate"]          # PCをプレートの上に置く
}

# タスクの完了状態管理 - 細分化されたステップ
completed_tasks = {
    # テレビ操作
    "step1_tv_operate": False,
    
    # 椅子移動の4段階
    "step2a_chair_approach": False,
    "step2b_chair_pickup": False,
    "step2c_chair_move_to_area": False,
    "step2d_chair_place": False,
    
    # PCプレート移動の4段階
    "step3a_plate_approach": False,
    "step3b_plate_pickup": False,
    "step3c_plate_move_to_area": False,
    "step3d_plate_place": False,
    
    # PC設置の4段階
    "step4a_pc_approach": False,
    "step4b_pc_pickup": False,
    "step4c_pc_move_to_plate": False,
    "step4d_pc_place": False
}

# DAG記法（Mermaid）- 細分化されたフロー
task_dag = """graph TD
    Step1[テレビのスイッチを操作する] --> Step2a[椅子に近づく]
    Step2a --> Step2b[椅子を拾う]
    Step2b --> Step2c[椅子を持ってChairAreaに移動]
    Step2c --> Step2d[椅子をChairAreaに置く]
    Step2d --> Step3a[PCプレートに近づく]
    Step3a --> Step3b[PCプレートを拾う]
    Step3b --> Step3c[PCプレートを持ってDaiAreaに移動]
    Step3c --> Step3d[PCプレートをDaiAreaに置く]
    Step3d --> Step4a[PCに近づく]
    Step4a --> Step4b[PCを拾う]
    Step4b --> Step4c[PCを持ってプレートの上に移動]
    Step4c --> Step4d[PCをプレートの上に置く]
    Step4d --> Complete[完了]"""

# タスクの詳細情報 - 細分化されたステップ
task_details = {
    # テレビ操作
    "step1_tv_operate": {
        "description": "テレビのスイッチを操作する",
        "details": "テレビに近づき、電源をONする",
        "completion_criteria": "テレビが点灯し、操作完了メッセージが表示される"
    },
    
    # 椅子移動の4段階
    "step2a_chair_approach": {
        "description": "椅子に近づく",
        "details": "移動可能な椅子の位置まで移動する",
        "completion_criteria": "椅子に隣接し、pickup操作が可能になる"
    },
    "step2b_chair_pickup": {
        "description": "椅子を拾う",
        "details": "pickup操作で椅子を持ち上げる",
        "completion_criteria": "椅子を持っている状態になる"
    },
    "step2c_chair_move_to_area": {
        "description": "椅子を持ってChairAreaに移動する",
        "details": "椅子を持った状態でChairArea（X=5.48, Z=-3.69）付近に移動する",
        "completion_criteria": "ChairArea付近に到達し、椅子を置く準備ができる"
    },
    "step2d_chair_place": {
        "description": "椅子をChairAreaに置く",
        "details": "椅子をChairArea（X=5.48, Z=-3.69）付近に置く。大体の位置で良い",
        "completion_criteria": "椅子がChairAreaに配置され、手から離れる"
    },
    
    # PCプレート移動の4段階
    "step3a_plate_approach": {
        "description": "PCプレートに近づく",
        "details": "移動可能なPCプレートの位置まで移動する",
        "completion_criteria": "PCプレートに隣接し、pickup操作が可能になる"
    },
    "step3b_plate_pickup": {
        "description": "PCプレートを拾う",
        "details": "pickup操作でPCプレートを持ち上げる",
        "completion_criteria": "PCプレートを持っている状態になる"
    },
    "step3c_plate_move_to_area": {
        "description": "PCプレートを持ってDaiAreaに移動する",
        "details": "PCプレートを持った状態でDaiArea（X=0.02, Z=3.55）付近に移動する",
        "completion_criteria": "DaiArea付近に到達し、PCプレートを置く準備ができる"
    },
    "step3d_plate_place": {
        "description": "PCプレートをDaiAreaに置く",
        "details": "PCプレートを+Z側中央エリア（X=0.02, Z=3.55）付近に置く",
        "completion_criteria": "PCプレートがDaiAreaに配置され、手から離れる"
    },
    
    # PC設置の4段階
    "step4a_pc_approach": {
        "description": "PCに近づく",
        "details": "移動可能なPCの位置まで移動する",
        "completion_criteria": "PCに隣接し、pickup操作が可能になる"
    },
    "step4b_pc_pickup": {
        "description": "PCを拾う",
        "details": "pickup操作でPCを持ち上げる",
        "completion_criteria": "PCを持っている状態になる"
    },
    "step4c_pc_move_to_plate": {
        "description": "PCを持ってプレートの上に移動する",
        "details": "PCを持った状態でDaiAreaのPCプレート上に移動する",
        "completion_criteria": "PCプレートの上に到達し、PCを置く準備ができる"
    },
    "step4d_pc_place": {
        "description": "PCをプレートの上に置く",
        "details": "PCをDaiAreaのPCプレートの上に正確に置く",
        "completion_criteria": "PCがプレートの上に配置され、手から離れる"
    }
}

def mark_task_completed(task_id):
    """タスクを完了状態にマークする"""
    if task_id in completed_tasks:
        completed_tasks[task_id] = True
        print(f"[TaskManager] タスク {task_id} が完了しました")
    else:
        print(f"[TaskManager] 警告: 未知のタスク {task_id}")

def is_task_completed(task_id):
    """タスクが完了しているかチェックする"""
    return completed_tasks.get(task_id, False)

def get_next_available_task():
    """次に実行可能なタスクを取得する"""
    # 定義された順序でタスクをチェック
    task_order = [
        "step1_tv_operate",
        "step2a_chair_approach", "step2b_chair_pickup", "step2c_chair_move_to_area", "step2d_chair_place",
        "step3a_plate_approach", "step3b_plate_pickup", "step3c_plate_move_to_area", "step3d_plate_place",
        "step4a_pc_approach", "step4b_pc_pickup", "step4c_pc_move_to_plate", "step4d_pc_place"
    ]
    
    for task_id in task_order:
        if not is_task_completed(task_id):
            # 依存関係をチェック
            deps = dependencies.get(task_id, [])
            if all(is_task_completed(dep) for dep in deps):
                return task_id
    return None

def get_available_tasks():
    """現在実行可能なタスクをすべて取得する"""
    available_tasks = []
    task_order = [
        "step1_tv_operate",
        "step2a_chair_approach", "step2b_chair_pickup", "step2c_chair_move_to_area", "step2d_chair_place",
        "step3a_plate_approach", "step3b_plate_pickup", "step3c_plate_move_to_area", "step3d_plate_place",
        "step4a_pc_approach", "step4b_pc_pickup", "step4c_pc_move_to_plate", "step4d_pc_place"
    ]
    
    for task_id in task_order:
        if not is_task_completed(task_id):
            # 依存関係をチェック
            deps = dependencies.get(task_id, [])
            if all(is_task_completed(dep) for dep in deps):
                available_tasks.append({
                    "task_id": task_id,
                    "description": task_details.get(task_id, {}).get("description", "説明なし"),
                    "details": task_details.get(task_id, {}).get("details", "詳細なし"),
                    "completion_criteria": task_details.get(task_id, {}).get("completion_criteria", "完了条件なし")
                })
    
    return available_tasks

def get_task_progress_summary():
    """タスクの進捗サマリーを取得する"""
    total_tasks = 13  # 全タスク数を13に更新
    completed_count = sum(1 for task in completed_tasks.values() if task)
    percentage = (completed_count / total_tasks) * 100
    
    return {
        "completed": completed_count,
        "total": total_tasks,
        "percentage": percentage,
        "task_status": completed_tasks.copy()
    }

def reset_all_tasks():
    """すべてのタスクをリセットする（デバッグ用）"""
    global completed_tasks
    completed_tasks = {
        "step1_tv_operate": False,
        "step2a_chair_approach": False,
        "step2b_chair_pickup": False,
        "step2c_chair_move_to_area": False,
        "step2d_chair_place": False,
        "step3a_plate_approach": False,
        "step3b_plate_pickup": False,
        "step3c_plate_move_to_area": False,
        "step3d_plate_place": False,
        "step4a_pc_approach": False,
        "step4b_pc_pickup": False,
        "step4c_pc_move_to_plate": False,
        "step4d_pc_place": False
    }
    print("[TaskManager] すべてのタスクがリセットされました")

def check_task_completion_criteria(logs):
    """ログからタスクの完了条件をチェックする - Unity側の実際のログパターンに対応"""
    log_text = " ".join(logs)
    
    # step1: テレビをONにする
    if not is_task_completed("step1_tv_operate"):
        tv_patterns = [
            "をONにしました！",           # Unity: "{deviceName}をONにしました！"
            "テレビをONにしました！",      # Alternative pattern
            "TVをONにしました！",         # Alternative pattern
            "TV操作・現在ON",             # Fallback pattern
            "interact（TVを操作・現在ON）"  # 実際のログパターン
        ]
        # TV操作が実行された時点で完了とする（ONになった場合）
        if any(pattern in log_text for pattern in tv_patterns):
            mark_task_completed("step1_tv_operate")
            return "step1_tv_operate"
        
        # さらに、interactコマンドの実行とON状態の確認
        if "interact" in log_text and "TVを操作" in log_text and "現在ON" in log_text:
            mark_task_completed("step1_tv_operate")
            return "step1_tv_operate"
    
    # step2a: 椅子に近づく
    if not is_task_completed("step2a_chair_approach"):
        chair_approach_patterns = [
            "椅子に近づきました",
            "椅子に隣接",
            "椅子が拾える距離",
            "椅子のそばに到着",
            "pickup（CarryableChairを拾う）",  # 実際のログパターン
            "pickup（椅子を拾う）",             # 日本語バリエーション
            "Z（椅子を拾う）"                  # 従来のパターン
        ]
        if any(pattern in log_text for pattern in chair_approach_patterns):
            mark_task_completed("step2a_chair_approach")
            return "step2a_chair_approach"
    
    # step2b: 椅子を拾う
    if not is_task_completed("step2b_chair_pickup"):
        chair_pickup_patterns = [
            "椅子を持ち上げました！",       # Unity: "{itemName}を持ち上げました！"
            "Chair を持ち上げました！",    # 英語名での椅子オブジェクト
            "chair を持ち上げました！",    # 小文字バリエーション
            "を持ち上げました！"            # より広範囲なマッチング
        ]
        # 椅子関連のオブジェクトのみを対象とする
        if any(pattern in log_text for pattern in chair_pickup_patterns) and ("椅子" in log_text or "chair" in log_text.lower()):
            mark_task_completed("step2b_chair_pickup")
            return "step2b_chair_pickup"
    
    # step2c: 椅子を持ってChairAreaに移動
    if not is_task_completed("step2c_chair_move_to_area"):
        # 椅子を持っている状態で、以下のいずれかの条件で移動完了とみなす
        chair_move_patterns = [
            "ChairAreaに到達",
            "ChairArea付近に到達",
            "椅子をChairAreaに移動",
            "pickup（床に置く）",  # ChairArea付近でpickupコマンドが利用可能になった
            "椅子を置く準備が完了"
        ]
        
        # 椅子を持っているかどうかを厳密にチェック
        holding_chair = False
        if "持っているもの" in log_text:
            # 「何も持っていません」「なし」「None」の場合は持っていない
            if any(negative in log_text for negative in ["何も持っていません", "持っているもの: なし", "持っているもの: None", "持っているもの:\nなし"]):
                holding_chair = False
            # 椅子関連を持っている場合
            elif any(chair_item in log_text for chair_item in ["CarryableChair", "椅子", "Chair", "chair"]):
                holding_chair = True
        
        # 椅子を持っている場合のみ移動完了判定を行う
        if holding_chair:
            if any(pattern in log_text for pattern in chair_move_patterns):
                mark_task_completed("step2c_chair_move_to_area")
                return "step2c_chair_move_to_area"
            # ChairAreaが周辺の状況に表示されていて、椅子を実際に持っている場合のみ移動完了
            if "ChairArea" in log_text and "周辺の状況" in log_text:
                mark_task_completed("step2c_chair_move_to_area")
                return "step2c_chair_move_to_area"
    
    # step2d: 椅子を置く
    if not is_task_completed("step2d_chair_place"):
        chair_place_patterns = [
            "椅子を置きました！",           # Unity: "{itemName}を置きました！場所: {details}"
            "Chair を置きました！",        # 英語名での椅子オブジェクト
            "chair を置きました！",        # 小文字バリエーション
            "椅子を置く作業が完了しました",   # Unity側で追加したメッセージ
            "を置きました！場所:"           # より広範囲なマッチング
        ]
        # 椅子関連のオブジェクトのみを対象とし、ChairArea付近への配置を確認
        if any(pattern in log_text for pattern in chair_place_patterns) and ("椅子" in log_text or "chair" in log_text.lower()):
            mark_task_completed("step2d_chair_place")
            return "step2d_chair_place"
        
        # 状況の変化による椅子配置の検出：椅子を持っていない状態でChairArea付近にいて、椅子を拾うコマンドが利用可能
        if ("holding_item\": None" in log_text or "持っているもの: なし" in log_text):
            if "ChairArea" in log_text and "pickup（CarryableChairを拾う）" in log_text:
                mark_task_completed("step2d_chair_place")
                return "step2d_chair_place"
    
    # step3a: PCプレートに近づく
    if not is_task_completed("step3a_plate_approach"):
        plate_approach_patterns = [
            "PCプレートに近づきました",
            "PCプレートに隣接",
            "PCプレートが拾える距離",
            "PCプレートのそばに到着",
            "PCプレートに到達しました",      # Unity側で追加したメッセージ
            "PCプレートを拾う準備が完了",     # Unity側で追加したメッセージ
            "pickup（PCプレートを拾う）",     # 実際のログパターン
            "Z（PCプレートを拾う）",        # PCプレートがpickup可能になった時点で接近完了
            "Z（プレートを拾う）"           # 短縮名
        ]
        if any(pattern in log_text for pattern in plate_approach_patterns):
            mark_task_completed("step3a_plate_approach")
            return "step3a_plate_approach"
    
    # step3b: PCプレートを拾う
    if not is_task_completed("step3b_plate_pickup"):
        plate_pickup_patterns = [
            "PCプレートを持ち上げました！",  # Unity: "{itemName}を持ち上げました！"
            "プレートを持ち上げました！",    # 短縮名
            "Plate を持ち上げました！",     # 英語名
            "plate を持ち上げました！"      # 小文字バリエーション
        ]
        # プレート関連のオブジェクトのみを対象とする
        if any(pattern in log_text for pattern in plate_pickup_patterns) and ("プレート" in log_text or "plate" in log_text.lower()):
            mark_task_completed("step3b_plate_pickup")
            return "step3b_plate_pickup"
    
    # step3c: PCプレートを持ってDaiAreaに移動
    if not is_task_completed("step3c_plate_move_to_area"):
        # PCプレートを持っている状態で、以下のいずれかの条件で移動完了とみなす
        plate_move_patterns = [
            "DaiAreaに到達",
            "DaiArea付近に到達", 
            "PCプレートをDaiAreaに移動",
            "pickup（床に置く）",  # DaiArea付近でpickupコマンドが利用可能になった
            "プレートを置く準備が完了"
        ]
        
        # PCプレートを持っているかどうかを厳密にチェック
        holding_plate = False
        if "持っているもの" in log_text:
            # 「何も持っていません」「なし」「None」の場合は持っていない
            if any(negative in log_text for negative in ["何も持っていません", "持っているもの: なし", "持っているもの: None", "持っているもの:\nなし"]):
                holding_plate = False
            # PCプレート関連を持っている場合
            elif any(plate_item in log_text for plate_item in ["PCプレート", "プレート", "Plate"]):
                holding_plate = True
        
        # PCプレートを持っている場合のみ移動完了判定を行う
        if holding_plate:
            if any(pattern in log_text for pattern in plate_move_patterns):
                mark_task_completed("step3c_plate_move_to_area")
                return "step3c_plate_move_to_area"
            # DaiAreaが周辺の状況に表示されていて、PCプレートを実際に持っている場合のみ移動完了
            if "DaiArea" in log_text and "周辺の状況" in log_text:
                mark_task_completed("step3c_plate_move_to_area")
                return "step3c_plate_move_to_area"
    
    # step3d: PCプレートを置く
    if not is_task_completed("step3d_plate_place"):
        plate_place_patterns = [
            "PCプレートを置きました！",     # Unity: "{itemName}を置きました！場所: {details}"
            "プレートを置きました！",       # 短縮名
            "Plate を置きました！",        # 英語名
            "plate を置きました！"         # 小文字バリエーション
        ]
        # プレート関連のオブジェクトのみを対象とし、DaiArea付近への配置を確認
        if any(pattern in log_text for pattern in plate_place_patterns) and ("プレート" in log_text or "plate" in log_text.lower()):
            mark_task_completed("step3d_plate_place")
            return "step3d_plate_place"
        
        # 状況の変化によるプレート配置の検出：プレートを持っていない状態でDaiArea付近にいて、プレートを拾うコマンドが利用可能
        if ("holding_item\": None" in log_text or "持っているもの: なし" in log_text):
            if "DaiArea" in log_text and ("pickup（PCプレートを拾う）" in log_text or "pickup（プレートを拾う）" in log_text):
                mark_task_completed("step3d_plate_place")
                return "step3d_plate_place"
    
    # step4a: PCに近づく
    if not is_task_completed("step4a_pc_approach"):
        pc_approach_patterns = [
            "PCに近づきました",
            "パソコンに近づきました",
            "PCに隣接",
            "PCが拾える距離",
            "PCのそばに到着",
            "Z（PCを拾う）",               # PCがpickup可能になった時点で接近完了
            "Z（パソコンを拾う）"           # 日本語名
        ]
        if any(pattern in log_text for pattern in pc_approach_patterns):
            mark_task_completed("step4a_pc_approach")
            return "step4a_pc_approach"
    
    # step4b: PCを拾う
    if not is_task_completed("step4b_pc_pickup"):
        pc_pickup_patterns = [
            "PCを持ち上げました！",         # Unity: "{itemName}を持ち上げました！"
            "パソコンを持ち上げました！",    # 日本語名
            "Computer を持ち上げました！",  # 英語名
            "PC を持ち上げました！"         # スペース付き
        ]
        # PC関連のオブジェクトのみを対象とする
        if any(pattern in log_text for pattern in pc_pickup_patterns) and ("PC" in log_text or "パソコン" in log_text or "computer" in log_text.lower()):
            mark_task_completed("step4b_pc_pickup")
            return "step4b_pc_pickup"
    
    # step4c: PCを持ってプレートの上に移動
    if not is_task_completed("step4c_pc_move_to_plate"):
        # PCを持っている状態で、以下のいずれかの条件で移動完了とみなす
        pc_move_patterns = [
            "プレートの上に到達",
            "PCプレートの上に到達",
            "プレート付近に到達",
            "pickup（床に置く）",  # プレート上でpickupコマンドが利用可能になった
            "PCを置く準備が完了"
        ]
        
        # PCを持っているかどうかを厳密にチェック
        holding_pc = False
        if "持っているもの" in log_text:
            # 「何も持っていません」「なし」「None」の場合は持っていない
            if any(negative in log_text for negative in ["何も持っていません", "持っているもの: なし", "持っているもの: None", "持っているもの:\nなし"]):
                holding_pc = False
            # PC関連を持っている場合
            elif any(pc_item in log_text for pc_item in ["PC", "パソコン", "Computer", "computer"]):
                holding_pc = True
        
        # PCを持っている場合のみ移動完了判定を行う
        if holding_pc:
            if any(pattern in log_text for pattern in pc_move_patterns):
                mark_task_completed("step4c_pc_move_to_plate")
                return "step4c_pc_move_to_plate"
            # PCプレートまたはDaiAreaが周辺の状況に表示されていて、PCを実際に持っている場合のみ移動完了
            if ("PCプレート" in log_text or "DaiArea" in log_text) and "周辺の状況" in log_text:
                mark_task_completed("step4c_pc_move_to_plate")
                return "step4c_pc_move_to_plate"
    
    # step4d: PCをプレートの上に置く
    if not is_task_completed("step4d_pc_place"):
        pc_place_patterns = [
            "PCを置きました！",            # Unity: "{itemName}を置きました！場所: {details}"
            "パソコンを置きました！",       # 日本語名
            "Computer を置きました！",     # 英語名
            "PC を置きました！"            # スペース付き
        ]
        # PC関連のオブジェクトのみを対象とし、プレートの上への設置を確認
        if any(pattern in log_text for pattern in pc_place_patterns) and ("PC" in log_text or "パソコン" in log_text or "computer" in log_text.lower()):
            mark_task_completed("step4d_pc_place")
            return "step4d_pc_place"
        
        # 状況の変化によるPC配置の検出：PCを持っていない状態でプレート付近にいて、PCを拾うコマンドが利用可能
        if ("holding_item\": None" in log_text or "持っているもの: なし" in log_text):
            if ("PCプレート" in log_text or "DaiArea" in log_text) and ("pickup（PCを拾う）" in log_text or "pickup（パソコンを拾う）" in log_text):
                mark_task_completed("step4d_pc_place")
                return "step4d_pc_place"
    
    return None

def get_current_task_group():
    """現在のタスクグループを取得（メインタスクの識別用）"""
    next_task = get_next_available_task()
    if not next_task:
        return "completed"
    
    if next_task.startswith("step1"):
        return "tv_operation"
    elif next_task.startswith("step2"):
        return "chair_movement"
    elif next_task.startswith("step3"):
        return "plate_movement"
    elif next_task.startswith("step4"):
        return "pc_placement"
    
    return "unknown"

def get_task_group_progress(group_name):
    """タスクグループの進捗状況を取得"""
    group_mappings = {
        "tv_operation": ["step1_tv_operate"],
        "chair_movement": ["step2a_chair_approach", "step2b_chair_pickup", "step2c_chair_move_to_area", "step2d_chair_place"],
        "plate_movement": ["step3a_plate_approach", "step3b_plate_pickup", "step3c_plate_move_to_area", "step3d_plate_place"],
        "pc_placement": ["step4a_pc_approach", "step4b_pc_pickup", "step4c_pc_move_to_plate", "step4d_pc_place"]
    }
    
    if group_name not in group_mappings:
        return None
    
    tasks = group_mappings[group_name]
    completed = sum(1 for task in tasks if is_task_completed(task))
    total = len(tasks)
    
    return {
        "completed": completed,
        "total": total,
        "percentage": (completed / total) * 100,
        "current_step": next((task for task in tasks if not is_task_completed(task)), None)
    }