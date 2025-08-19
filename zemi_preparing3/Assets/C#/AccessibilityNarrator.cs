// アクセシビリティナレーター
// - プレイヤー周辺のオブジェクト検出 / ログ整形
// 構成: 4=データ収集、5=検出・判定(4で使用)、6=ユーティリティ(6.1〜6.4)

using UnityEngine;
using System.Collections.Generic;
using System.Linq;
using System.Collections; // Added for IEnumerator

public class AccessibilityNarrator : MonoBehaviour
{
    [Header("Detection Settings")]
    public float detectionRadius = 5.0f;
    public float forwardRayDistance = 3.0f;
    public LayerMask detectionLayer = -1;
    
    [Header("Log Management Settings")]
    public bool enableActionLogging = true; // アクションログの有効/無効
    public bool suppressTechnicalLogs = true; // 技術的ログを非表示にする
    public bool enableDebugOutput = false; // デバッグ用の自動ログ出力
    
    private Camera playerCamera;
    private PlayerInteractionController interactionController;
    
    // シングルトンインスタンス
    public static AccessibilityNarrator Instance;
    
    // 前回の近くのオブジェクト（重複通知を避けるため）
    private string lastNearbyItem = "";
    private string lastNearbyTV = "";
    
    // アクションログ管理
    private List<string> actionLogs = new List<string>();
    private bool hasNewActionData = false;

    #region 1. Core lifecycle & setup
    void Awake()
    {
        // シングルトンパターンの実装
        if (Instance == null)
        {
            Instance = this;
        }
        else
        {
            Destroy(gameObject);
        }
        
        // 技術的ログを非表示にする
        if (suppressTechnicalLogs)
        {
            // InputSystemの詳細ログを非表示
            UnityEngine.Debug.developerConsoleVisible = false;
            Application.logMessageReceived += FilterLogs;
        }
    }
    
    void OnDestroy()
    {
        if (suppressTechnicalLogs)
        {
            Application.logMessageReceived -= FilterLogs;
        }
    }
    
    void Start()
    {
        // プレイヤーのカメラを取得
        playerCamera = Camera.main;
        if (playerCamera == null)
        {
            playerCamera = FindFirstObjectByType<Camera>();
        }
        
        // プレイヤーのInteractionControllerを取得
        interactionController = GetComponent<PlayerInteractionController>();
    }

    /// <summary>
    /// 技術的ログをフィルタリングして非表示にする
    /// </summary>
    private void FilterLogs(string logString, string stackTrace, LogType type)
    {
        // 技術的ログを非表示にする
        if (logString.Contains("Input called with state") ||
            logString.Contains("StarterAssetsInputs") ||
            logString.Contains("InputSystem") ||
            logString.Contains("NativeInputSystem") ||
            logString.Contains("UnityEngineInternal"))
        {
            return; // 表示しない
        }
    }

    /// <summary>
    /// (補助) コマンド完了時の内部処理。実装が別途ある場合は置き換えてください。
    /// </summary>
    private void OnCommandFinished() { /* TODO: 必要なら処理を追加 */ }
    #endregion

    #region 2. Public API
    /// <summary>
    /// LLMCommunicatorからの要求に応じて現在の状況ログを収集・返却
    /// </summary>
    public List<string> CollectCurrentSituationLogs()
    {
        List<string> allData = new List<string>();
        
        // 1. 基本状況情報を取得
        List<string> situationData = GatherCurrentSituationData();
        allData.AddRange(situationData);
        
        // 2. 実行したアクションセクション
        List<string> recentActions = GatherRecentActionInfo();
        if (recentActions.Count > 0)
        {
            allData.Add("[実行したアクション]");
            allData.AddRange(recentActions);
        }
        
        // 3. 検出情報セクション
        List<string> detectionInfo = GatherDetectionInfo();
        if (detectionInfo.Count > 0)
        {
            allData.Add("[検出情報]");
            allData.AddRange(detectionInfo);
        }
        
        if (enableDebugOutput)
        {
            Debug.Log($"[Narrator] 状況ログを収集完了（{allData.Count}件のデータ）");
        }
        
        return allData;
    }

    /// <summary>
    /// コマンド実行完了通知
    /// </summary>
    public void OnCommandCompleted()
    {
        // コマンド実行終了（ログ出力再開など）
        OnCommandFinished();
        
        if (enableDebugOutput)
        {
            Debug.Log("[Narrator] コマンド実行完了");
        }
        
        // LLMCommunicatorに通知
        if (LLMCommunicator.Instance != null)
        {
            LLMCommunicator.Instance.OnCommandCompleted();
        }
    }
    #endregion

    #region 3. Event Handlers
    /// <summary>
    /// アイテムを拾った時のナレーション
    /// </summary>
    public void OnItemPickedUp(string itemName)
    {
        if (!enableActionLogging) return;
        
        // 「Dai」を「PCプレート」として表示
        string displayName = itemName;
        if (itemName == "Dai")
        {
            displayName = "PCプレート";
        }
        
        string actionMessage = $"{displayName}を持ち上げました！pickupコマンドで置くことができます。";
        actionLogs.Add(actionMessage);
        hasNewActionData = true;
        
        if (enableDebugOutput)
        {
            Debug.Log(actionMessage);
        }
    }
    
    /// <summary>
    /// アイテムを置いた時のナレーション
    /// </summary>
    public void OnItemDropped(string itemName, Vector3 dropPosition)
    {
        if (!enableActionLogging) return;
        
        // ドロップした場所の詳細を取得
        string dropLocationDetails = GetDropLocationDetails(dropPosition);
        
        // 「Dai」を「PCプレート」として表示
        string displayName = itemName;
        if (itemName == "Dai")
        {
            displayName = "PCプレート";
        }
        
        string actionMessage = $"{displayName}を置きました！場所: {dropLocationDetails}";
        actionLogs.Add(actionMessage);
        hasNewActionData = true;
        
        if (enableDebugOutput)
        {
            Debug.Log(actionMessage);
        }
    }
    
    /// <summary>
    /// 近くのアイテムを検出した時のナレーション（ログは抑制）
    /// </summary>
    public void OnNearbyItemDetected(string itemName, float distance)
    {
        if (!enableActionLogging) return;
        
        // 重複を避ける
        string currentItem = $"{itemName}_{distance:F1}";
        if (lastNearbyItem == currentItem) return;
        lastNearbyItem = currentItem;
        
        // 方角を計算（必要に応じて利用）
        ItemPickup nearbyItem = interactionController?.CurrentNearbyItem;
        if (nearbyItem != null)
        {
            Vector3 directionVector = (nearbyItem.transform.position - transform.position).normalized;
            _ = GetDirectionText(directionVector); // 方向テキスト計算のみ
        }
        
        // 表示名の正規化
        _ = (itemName == "Dai") ? "PCプレート" : itemName;
        
        // アイテム検出ログは完全に除外
    }
    
    /// <summary>
    /// TVを操作した時のナレーション
    /// </summary>
    public void OnTVToggled(string deviceName, bool isOn)
    {
        if (!enableActionLogging) return;
        
        string stateText = isOn ? "ON" : "OFF";
        string actionMessage = $"{deviceName}を{stateText}にしました！";
        actionLogs.Add(actionMessage);
        hasNewActionData = true;
        
        if (enableDebugOutput)
        {
            Debug.Log(actionMessage);
        }
    }
    
    /// <summary>
    /// 近くのTVを検出した時のナレーション（ログは抑制）
    /// </summary>
    public void OnNearbyTVDetected(string deviceName, float distance, bool isOn)
    {
        if (!enableActionLogging) return;
        
        // 重複を避ける
        string stateText = isOn ? "ON" : "OFF";
        string currentTV = $"{deviceName}_{distance:F1}_{stateText}";
        if (lastNearbyTV == currentTV) return;
        lastNearbyTV = currentTV;
        
        // 方角を計算（必要に応じて利用）
        TVInteract nearbyTV = interactionController?.CurrentNearbyTV;
        if (nearbyTV != null)
        {
            Vector3 directionVector = (nearbyTV.GetButtonPosition() - transform.position).normalized;
            _ = GetDirectionText(directionVector);
        }
    }

    /// <summary>
    /// 近くのアイテムリセット
    /// </summary>
    public void ResetNearbyItem() => lastNearbyItem = "";
    
    /// <summary>
    /// 近くのTVリセット
    /// </summary>
    public void ResetNearbyTV() => lastNearbyTV = "";
    #endregion

    #region 4. データ収集メソッド（CollectCurrentSituationLogsから呼ばれる）
    /// <summary>
    /// 基本状況データを収集
    /// </summary>
    private List<string> GatherCurrentSituationData()
    {
        List<string> situationData = new List<string>();
        
        // 現在の状況タイトル
        situationData.Add("=== 現在の状況 ===");
        
        // 現在地情報
        situationData.Add("[現在地]");
        Vector3 pos = transform.position;
        situationData.Add($"座標（X={pos.x:F1}, Z={pos.z:F1}）");
        
        
        // 周辺の状況
        situationData.Add("[周辺の状況]");
        var objects = GetImportantObjectsPositions();
        var tables = GetTablePositions();
        
        var allObjects = new List<string>();
        allObjects.AddRange(objects);
        allObjects.AddRange(tables);
        
        if (allObjects.Count > 0)
        {
            situationData.AddRange(allObjects);
        }
        else
        {
            situationData.Add("周辺に重要なオブジェクトはありません");
        }
        
        // 持っているもの
        situationData.Add("[持っているもの]");
        if (interactionController != null && interactionController.CarriedItem != null)
        {
            situationData.Add(interactionController.CarriedItem.itemName);
        }
        else
        {
            situationData.Add("何も持っていません");
        }
        
        // 可能なコマンド
        situationData.Add("[可能なコマンド]");
        List<string> commands = GetAvailableMovementCommands();
        
        // アイテム関連のコマンド
        if (interactionController != null && interactionController.CurrentNearbyItem != null && interactionController.CarriedItem == null)
        {
            string itemName = interactionController.CurrentNearbyItem.itemName;
            if (itemName == "Dai") itemName = "PCプレート";
            commands.Add($"pickup（{itemName}を拾う）");
        }
        
        // ドロップコマンド
        if (interactionController != null && interactionController.CarriedItem != null)
        {
            string dropInfo = GetDropLocationInfo();
            commands.Add(dropInfo);
        }
        
        // TV操作コマンド
        if (interactionController != null && interactionController.CurrentNearbyTV != null)
        {
            string tvState = interactionController.CurrentNearbyTV.IsOn() ? "ON" : "OFF";
            commands.Add($"interact（{interactionController.CurrentNearbyTV.deviceName}を操作・現在{tvState}）");
        }
        
        if (commands.Count > 0)
        {
            situationData.Add($"  {string.Join("、", commands)}");
        }
        else
        {
            situationData.Add("  移動不可");
        }
        
        
        return situationData;
    }
    
    /// <summary>
    /// 検出情報を収集（アイテム検出、TV検出、エリア到達等）
    /// </summary>
    private List<string> GatherDetectionInfo()
    {
        List<string> detectionInfo = new List<string>();
        
        // エリア到達チェック
        CheckAreaArrivalForLog(detectionInfo);
        
        // 近くのアイテム検出
        CheckNearbyItemsForLog(detectionInfo);
        
        // 近くのTV検出
        CheckNearbyTVsForLog(detectionInfo);
        
        return detectionInfo;
    }
    
    /// <summary>
    /// 最近のアクション情報を収集（アイテム拾い上げ、設置、TV操作等）
    /// </summary>
    private List<string> GatherRecentActionInfo()
    {
        List<string> actionInfo = new List<string>();
        
        // 蓄積されたアクションログがあれば追加
        if (actionLogs.Count > 0)
        {
            actionInfo.AddRange(actionLogs);
            // 取得後にクリア（次回は新しいアクションのみ）
            actionLogs.Clear();
            hasNewActionData = false;
        }
        
        return actionInfo;
    }
    #endregion

    #region 5. 検出・判定メソッド（データ収集で使用）
    /// <summary>
    /// 重要なオブジェクト（TV、PC、椅子、テレビ台）の位置を取得
    /// </summary>
    private List<string> GetImportantObjectsPositions()
    {
        List<string> importantObjects = new List<string>();
        
        // シーン内のすべてのオブジェクトを検索（距離制限なし）
        GameObject[] allObjects = FindObjectsByType<GameObject>(FindObjectsSortMode.None);
        
        Dictionary<string, List<(Vector3, GameObject)>> objectGroups = new Dictionary<string, List<(Vector3, GameObject)>>();
        HashSet<GameObject> processedObjects = new HashSet<GameObject>();
        
        foreach (GameObject obj in allObjects)
        {
            if (obj == gameObject) continue; // 自分自身は除外
            
            // 既に処理済みのオブジェクトかその子オブジェクトの場合はスキップ
            GameObject rootObject = GetRootImportantObject(obj);
            if (rootObject != null && !processedObjects.Contains(rootObject))
            {
                string objName = GetImportantObjectName(rootObject);
                if (!string.IsNullOrEmpty(objName))
                {
                    if (!objectGroups.ContainsKey(objName))
                    {
                        objectGroups[objName] = new List<(Vector3, GameObject)>();
                    }
                    objectGroups[objName].Add((rootObject.transform.position, rootObject));
                    processedObjects.Add(rootObject);
                }
            }
        }
        
        // 重要なオブジェクトの順序を定義
        string[] priorityOrder = { "テレビ", "PC", "パソコン", "運搬可能な椅子", "台" };
        
        foreach (string priority in priorityOrder)
        {
            if (objectGroups.ContainsKey(priority))
            {
                var positions = objectGroups[priority];
                
                if (positions.Count == 1)
                {
                    Vector3 objectPos = positions[0].Item1;
                    Vector3 playerPos = transform.position;
                    Vector3 diff = objectPos - playerPos;
                    
                    string xStr = diff.x >= 0 ? $"+{diff.x:F1}" : $"{diff.x:F1}";
                    string zStr = diff.z >= 0 ? $"+{diff.z:F1}" : $"{diff.z:F1}";
                    string displayName = priority == "台" ? "PCプレート" : priority;
                    importantObjects.Add($"x方向に{xStr}、z方向に{zStr}に{displayName}");
                }
                else
                {
                    // 複数ある場合は最も近いものを表示
                    var nearest = positions.OrderBy(p => Vector3.Distance(transform.position, p.Item1)).First();
                    Vector3 objectPos = nearest.Item1;
                    Vector3 playerPos = transform.position;
                    Vector3 diff = objectPos - playerPos;
                    
                    string xStr = diff.x >= 0 ? $"+{diff.x:F1}" : $"{diff.x:F1}";
                    string zStr = diff.z >= 0 ? $"+{diff.z:F1}" : $"{diff.z:F1}";
                    string displayPriority = priority == "台" ? "PCプレート" : priority;
                    string countText = GetCountText(displayPriority, positions.Count);
                    importantObjects.Add($"x方向に{xStr}、z方向に{zStr}に{countText}");
                }
            }
        }
        
        // 仮想エリア（ChairArea、DaiArea）の位置情報を追加
        AddVirtualAreas(importantObjects);
        
        return importantObjects;
    }

    /// <summary>
    /// 移動可能な方向のコマンドを取得
    /// </summary>
    private List<string> GetAvailableMovementCommands()
    {
        List<string> availableCommands = new List<string>();
        
        // 各方向をチェック
        Vector3[] directions = {
            Vector3.forward,  // +Z
            Vector3.right,    // +X
            Vector3.back,     // -Z
            Vector3.left      // -X
        };
        
        string[] directionNames = { "+Z", "+X", "-Z", "-X" };
        
        for (int i = 0; i < directions.Length; i++)
        {
            string obstacle = GetObstacleInDirection(directions[i]);
            if (string.IsNullOrEmpty(obstacle))
            {
                availableCommands.Add(directionNames[i]);
            }
            // 利用不可のコマンドは表示しない
        }
        
        return availableCommands;
    }

    /// <summary>
    /// エリア到達チェック（ログ用）
    /// </summary>
    private void CheckAreaArrivalForLog(List<string> messages)
    {
        Vector3 currentPosition = transform.position;
        PlayerInteractionController interaction = GetComponent<PlayerInteractionController>();
        bool hasItem = interaction != null && interaction.CarriedItem != null;
        string heldItemName = hasItem ? interaction.CarriedItem.itemName : "";
        
        // ChairArea到達チェック（椅子を持っている場合）
        if (heldItemName.Contains("Chair") || heldItemName.Contains("椅子"))
        {
            Vector3 chairAreaCenter = new Vector3(5.48f, currentPosition.y, -3.69f);
            float chairAreaDistance = Vector3.Distance(currentPosition, chairAreaCenter);
            if (chairAreaDistance <= 2.5f)
            {
                messages.Add("ChairAreaに到達。椅子を置く準備が完了。");
            }
        }
        
        // PCプレート持参時のDaiArea到達チェック
        if (heldItemName.Contains("Dai") || heldItemName.Contains("プレート"))
        {
            Vector3 daiAreaCenter = new Vector3(0.02f, currentPosition.y, 3.55f);
            float daiAreaDistance = Vector3.Distance(currentPosition, daiAreaCenter);
            if (daiAreaDistance <= 2.5f)
            {
                messages.Add("DaiAreaに到達。PCプレートを置く準備が完了。");
            }
        }
        
        // PC持参時のプレート上到達チェック
        if (heldItemName.Contains("PC") || heldItemName.Contains("パソコン"))
        {
            Vector3 daiAreaCenter = new Vector3(0.02f, currentPosition.y, 3.55f);
            float plateDistance = Vector3.Distance(currentPosition, daiAreaCenter);
            if (plateDistance <= 2.0f)
            {
                messages.Add("PCプレートの上に到達。PCを置く準備が完了。");
            }
        }
    }
    
    /// <summary>
    /// 近くのアイテム検出（ログ用）
    /// </summary>
    private void CheckNearbyItemsForLog(List<string> messages)
    {
        if (interactionController != null && interactionController.CurrentNearbyItem != null && interactionController.CarriedItem == null)
        {
            string itemName = interactionController.CurrentNearbyItem.itemName;
            float distance = Vector3.Distance(transform.position, interactionController.CurrentNearbyItem.transform.position);
            
            Vector3 directionVector = (interactionController.CurrentNearbyItem.transform.position - transform.position).normalized;
            string direction = GetDirectionText(directionVector);
            
            string displayName = itemName == "Dai" ? "PCプレート" : itemName;
            messages.Add($"{direction}約{distance:F1}メートルに{displayName}あり。pickupコマンドで持ち上げ可能");
        }
    }
    
    /// <summary>
    /// 近くのTV検出（ログ用）
    /// </summary>
    private void CheckNearbyTVsForLog(List<string> messages)
    {
        if (interactionController != null && interactionController.CurrentNearbyTV != null)
        {
            string deviceName = interactionController.CurrentNearbyTV.deviceName;
            bool isOn = interactionController.CurrentNearbyTV.IsOn();
            float distance = Vector3.Distance(transform.position, interactionController.CurrentNearbyTV.GetButtonPosition());
            
            Vector3 directionVector = (interactionController.CurrentNearbyTV.GetButtonPosition() - transform.position).normalized;
            string direction = GetDirectionText(directionVector);
            
            string stateText = isOn ? "ON" : "OFF";
            messages.Add($"{direction}約{distance:F1}メートルに{deviceName}あり。{stateText}・interactコマンドで操作可能");
        }
    }

    /// <summary>
    /// 周辺のテーブルの位置を取得（3メートル範囲）
    /// </summary>
    private List<string> GetTablePositions()
    {
        List<string> tablePositions = new List<string>();
        
        // テーブルの名前リスト
        string[] tableNames = { "Table_NW", "Table_SE", "Table_SW", "Table_NE" };
        
        foreach (string tableName in tableNames)
        {
            GameObject tableObj = GameObject.Find(tableName);
            if (tableObj != null)
            {
                float distance = Vector3.Distance(transform.position, tableObj.transform.position);
                if (distance <= 3.0f) // 3メートル範囲
                {
                    Vector3 diff = tableObj.transform.position - transform.position;
                    string xStr = diff.x >= 0 ? $"+{diff.x:F1}" : $"{diff.x:F1}";
                    string zStr = diff.z >= 0 ? $"+{diff.z:F1}" : $"{diff.z:F1}";
                    string tableDescription = GetTableDescription(tableName);
                    tablePositions.Add($"x方向に{xStr}、z方向に{zStr}に{tableDescription}");
                }
            }
        }
        
        return tablePositions;
    }
    #endregion

    #region 6. ユーティリティメソッド（関連メソッドをグループ化）
    #region 6.1 ドロップ関連
    private string GetDropLocationInfo()
    {
        if (playerCamera == null) return "pickup（胸元の真下に置く）";
        
        // 現在持っているアイテムの位置（胸元）を基準とする
        Vector3 dropPosition;
        if (interactionController != null && interactionController.CarriedItem != null)
        {
            // 持っているアイテムの真下に置く
            Vector3 carryPosition = interactionController.CarriedItem.transform.position;
            dropPosition = new Vector3(carryPosition.x, transform.position.y, carryPosition.z);
        }
        else
        {
            // アイテムを持っていない場合はプレイヤー位置
            dropPosition = transform.position;
        }
        
        // 下方向にレイを飛ばして、置ける表面を探す
        RaycastHit hit;
        Vector3 rayOrigin = dropPosition + Vector3.up * 2f; // 2メートル上から
        Vector3 rayDirection = Vector3.down;
        
        if (Physics.Raycast(rayOrigin, rayDirection, out hit, 4f, detectionLayer))
        {
            // 置く場所の種類を判定
            string surfaceType = GetSurfaceType(hit.collider.gameObject);
            
            return $"pickup（{surfaceType}に置く）";
        }
        else
        {
            // レイが何にも当たらない場合は、地面に置く予定として表示
            return $"pickup（地面に置く）";
        }
    }

    /// <summary>
    /// ドロップした場所の詳細を取得
    /// </summary>
    private string GetDropLocationDetails(Vector3 dropPosition)
    {
        Vector3 direction = (dropPosition - transform.position).normalized;
        string directionText = GetDirectionText(direction);
        float distance = Vector3.Distance(transform.position, dropPosition);
        string coordinates = $"座標X:{dropPosition.x:F1}, Z:{dropPosition.z:F1}";
        
        // 特定エリアの検出
        string locationDetails = DetectSpecialArea(dropPosition);
        if (!string.IsNullOrEmpty(locationDetails))
        {
            return $"{coordinates}、{locationDetails}";
        }
        
        return $"{coordinates}、{directionText}約{distance:F1}メートル";
    }
    
    private string GetSurfaceType(GameObject surface)
    {
        // まず現在のオブジェクトをチェック
        string surfaceResult = CheckSurfaceTypeName(surface);
        if (!string.IsNullOrEmpty(surfaceResult))
        {
            return surfaceResult;
        }
        
        // 親オブジェクトをチェック
        Transform parent = surface.transform.parent;
        while (parent != null)
        {
            string parentResult = CheckSurfaceTypeName(parent.gameObject);
            if (!string.IsNullOrEmpty(parentResult))
            {
                return parentResult;
            }
            parent = parent.parent;
        }
        
        // どれにも該当しない場合
        return $"{surface.name}の上";
    }
    
    private string CheckSurfaceTypeName(GameObject obj)
    {
        string name = obj.name.ToLower();
        
        if (name.Contains("table"))
            return "テーブルの上";
        else if (name.Contains("desk"))
            return "デスクの上";
        else if (name.Contains("chairarea"))
            return "椅子エリア";
        else if (name.Contains("chair"))
            return "椅子の上";
        else if (name.Contains("daiarea"))
            return "台エリア";
        else if (name.Contains("dai"))
            return "台の上";
        else if (name.Contains("floor") || name.Contains("flore"))
            return "床";
        else if (name.Contains("ground"))
            return "地面";
        
        // コンポーネントをチェックして詳細を取得
        ItemPickup itemPickup = obj.GetComponent<ItemPickup>();
        if (itemPickup != null)
        {
            return $"{itemPickup.itemName}の上";
        }
        
        TVInteract tvInteract = obj.GetComponent<TVInteract>();
        if (tvInteract != null)
        {
            return $"{tvInteract.deviceName}の上";
        }
        
        // 該当しない場合は空文字列を返す
        return "";
    }
    #endregion

    #region 6.2 オブジェクト識別関連
    /// <summary>
    /// 重要なオブジェクトかどうかを判定
    /// </summary>
    private bool IsImportantObject(string objName)
    {
        return objName == "椅子" || objName == "運搬可能な椅子" || objName == "テレビ" || 
               objName == "パソコン" || objName == "台" || objName == "テーブル";
    }
    
    /// <summary>
    /// 重要なオブジェクトのルートオブジェクトを取得
    /// </summary>
    private GameObject GetRootImportantObject(GameObject obj)
    {
        Transform current = obj.transform;
        GameObject bestMatch = null;
        
        // 上に向かって辿り、適切な重要なオブジェクトを見つける
        while (current != null)
        {
            string currentName = current.name.ToLower();
            
            // 個別のオブジェクトを優先（Table (1), Table (2) など）
            if (currentName == "pc" ||
                currentName == "tv" ||
                currentName == "dai" ||
                (currentName == "table" || currentName.StartsWith("table ")) ||
                currentName == "carryablechair")
            {
                bestMatch = current.gameObject;
                // 個別オブジェクトが見つかったら、それ以上上は探さない
                break;
            }
            
            // グループオブジェクトは最後の手段として保持
            if (currentName == "tables")
            {
                if (bestMatch == null)
                {
                    bestMatch = current.gameObject;
                }
            }
            
            // コンポーネントもチェック
            ItemPickup itemPickup = current.GetComponent<ItemPickup>();
            TVInteract tvInteract = current.GetComponent<TVInteract>();
            if (itemPickup != null || tvInteract != null)
            {
                bestMatch = current.gameObject;
                break;
            }
            
            current = current.parent;
        }
        
        return bestMatch;
    }
    
    /// <summary>
    /// 重要なオブジェクトの名前を取得
    /// </summary>
    private string GetImportantObjectName(GameObject obj)
    {
        string name = obj.name.ToLower();
        
        // 正確なオブジェクト名に基づいて判定
        if (name == "carryablechair")
            return "運搬可能な椅子";
        else if (name == "tables" || name == "table" || name.StartsWith("table "))
            return "テーブル";
        else if (name == "pc")
            return "パソコン";
        else if (name == "tv")
            return "テレビ";
        else if (name == "dai")
            return "台";
        
        // ItemPickupコンポーネントがあるかチェック
        ItemPickup itemPickup = obj.GetComponent<ItemPickup>();
        if (itemPickup != null)
        {
            return itemPickup.itemName;
        }
        
        // TVInteractコンポーネントがあるかチェック
        TVInteract tvInteract = obj.GetComponent<TVInteract>();
        if (tvInteract != null)
        {
            return tvInteract.deviceName;
        }
        
        return "";
    }

    private string GetObjectDescription(GameObject obj)
    {
        // まず親オブジェクトを確認して重要なオブジェクトかチェック
        GameObject rootObject = GetRootImportantObject(obj);
        if (rootObject != null)
        {
            return GetImportantObjectName(rootObject);
        }
        
        string name = obj.name.ToLower();
        
        // 不要なオブジェクトを除外
        if (name.Contains("wall") || name.Contains("floor") || name.Contains("flore"))
            return ""; // 壁や床は除外
        else if (name.Contains("cube") || name.Contains("cylinder") || name.Contains("sphere"))
            return ""; // 基本的な形状オブジェクトは除外
        else if (name.Contains("collider") || name.Contains("trigger"))
            return ""; // コライダーは除外
        else if (name.Contains("camera") || name.Contains("light"))
            return ""; // カメラやライトは除外
        
        // それ以外は空文字列で除外
        return "";
    }
    
    /// <summary>
    /// 前方の障害物検出（机、TV等も含む）
    /// </summary>
    private string GetObjectDescriptionWithObstacles(GameObject obj)
    {
        string name = obj.name.ToLower();
        
        // まず親オブジェクトから確認（Cubeなどの場合）
        Transform checkObject = obj.transform;
        while (checkObject != null)
        {
            string checkName = checkObject.name.ToLower();
            
            // 正確なオブジェクト名に基づいて判定
            if (checkName == "chairs" || checkName.StartsWith("chair"))
                return "椅子";
            else if (checkName == "tables" || checkName == "table" || checkName.StartsWith("table "))
                return "テーブル";
            else if (checkName == "pc")
                return "パソコン";
            else if (checkName == "tv")
                return "テレビ";
            else if (checkName == "dai")
                return "台";
            else if (checkName.Contains("wall"))
                return "壁";
            else if (checkName.Contains("door"))
                return "ドア";
            else if (checkName.Contains("desk"))
                return "机";
            
            // ItemPickupコンポーネントがあるかチェック
            ItemPickup itemPickup = checkObject.GetComponent<ItemPickup>();
            if (itemPickup != null)
            {
                return itemPickup.itemName;
            }
            
            // TVInteractコンポーネントがあるかチェック
            TVInteract tvInteract = checkObject.GetComponent<TVInteract>();
            if (tvInteract != null)
            {
                return tvInteract.deviceName;
            }
            
            checkObject = checkObject.parent;
        }
        
        // 除外するオブジェクト
        if (name.Contains("floor") || name.Contains("flore"))
            return ""; // 床は除外
        else if (name.Contains("ground"))
            return ""; // 地面は除外
        else if (name.Contains("collider") || name.Contains("trigger"))
            return ""; // コライダーは除外
        
        // その他の障害物として扱う
        return obj.name;
    }

    /// <summary>
    /// 障害物オブジェクトの名前を取得
    /// </summary>
    private string GetObstacleObjectName(GameObject obj)
    {
        // 重要なオブジェクトのルートを取得
        GameObject rootObject = GetRootImportantObject(obj);
        if (rootObject != null)
        {
            string importantName = GetImportantObjectName(rootObject);
            if (!string.IsNullOrEmpty(importantName))
            {
                return importantName;
            }
        }
        
        // 一般的なオブジェクト名を取得
        string objName = GetObjectDescription(obj);
        if (!string.IsNullOrEmpty(objName))
        {
            return objName;
        }
        
        // フォールバック：オブジェクト名そのまま
        string name = obj.name.ToLower();
        if (name.Contains("wall"))
            return "壁";
        else if (name.Contains("door"))
            return "ドア";
        else if (name.Contains("table"))
            return "テーブル";
        else if (name.Contains("chair"))
            return "椅子";
        else
            return "障害物";
    }
    #endregion

    #region 6.3 移動・障害物関連
    /// <summary>
    /// 指定した方向に移動可能かチェック
    /// </summary>
    private bool CanMoveInDirection(Vector3 direction)
    {
        return string.IsNullOrEmpty(GetObstacleInDirection(direction));
    }
    
    /// <summary>
    /// 指定した方向にある障害物の名前を取得（障害物がない場合は空文字を返す）
    /// </summary>
    private string GetObstacleInDirection(Vector3 direction)
    {
        // プレイヤーの現在位置から少し上の位置を起点とする（地面を避けるため）
        Vector3 rayOrigin = transform.position + Vector3.up * 1.0f;
        
        // 指定された方向に1.5メートル先まで障害物がないかチェック
        float checkDistance = 1.5f;
        
        RaycastHit hit;
        if (Physics.Raycast(rayOrigin, direction, out hit, checkDistance, detectionLayer))
        {
            // ヒットしたオブジェクトが床や地面の場合はOK
            string hitObjectName = hit.collider.name.ToLower();
            if (hitObjectName.Contains("floor") || hitObjectName.Contains("flore") || hitObjectName.Contains("ground"))
            {
                // 床の場合は障害物ではない
            }
            else
            {
                // 障害物の名前を取得
                string obstacleName = GetObstacleObjectName(hit.collider.gameObject);
                if (!string.IsNullOrEmpty(obstacleName))
                {
                    return obstacleName;
                }
            }
        }
        
        // 地面があるかもチェック（落下防止）- より緩い条件に変更
        Vector3 groundCheckOrigin = transform.position + direction * checkDistance + Vector3.up * 1.0f;
        if (!Physics.Raycast(groundCheckOrigin, Vector3.down, 3.0f, detectionLayer))
        {
            // 地面がない場合は移動不可（室内なので壁として扱う）
            return "壁";
        }
        
        return ""; // 障害物なし
    }
    #endregion

    #region 6.4 その他ヘルパー
    /// <summary>
    /// 特定エリア（ChairArea、DaiAreaなど）の検出
    /// </summary>
    private string DetectSpecialArea(Vector3 position)
    {
        // ChairArea（X=5.48, Z=-3.69）付近の検出
        Vector3 chairAreaCenter = new Vector3(5.48f, position.y, -3.69f);
        float chairAreaDistance = Vector3.Distance(position, chairAreaCenter);
        if (chairAreaDistance <= 2.0f)
        {
            return "ChairArea付近";
        }
        
        // DaiArea（X=0.02, Z=3.55）付近の検出
        Vector3 daiAreaCenter = new Vector3(0.02f, position.y, 3.55f);
        float daiAreaDistance = Vector3.Distance(position, daiAreaCenter);
        if (daiAreaDistance <= 2.0f)
        {
            return "DaiArea付近";
        }
        
        return "";
    }

    /// <summary>
    /// 仮想エリア（ChairArea、DaiArea）の位置情報を追加
    /// </summary>
    private void AddVirtualAreas(List<string> importantObjects)
    {
        Vector3 playerPos = transform.position;
        
        // ChairArea（X=5.48, Z=-3.69）の位置情報
        Vector3 chairAreaPos = new Vector3(5.48f, playerPos.y, -3.69f);
        float chairAreaDistance = Vector3.Distance(playerPos, chairAreaPos);
        
        // 一定範囲内にいる場合のみ表示（20メートル以内）
        if (chairAreaDistance <= 20.0f)
        {
            Vector3 chairAreaDiff = chairAreaPos - playerPos;
            string chairXStr = chairAreaDiff.x >= 0 ? $"+{chairAreaDiff.x:F1}" : $"{chairAreaDiff.x:F1}";
            string chairZStr = chairAreaDiff.z >= 0 ? $"+{chairAreaDiff.z:F1}" : $"{chairAreaDiff.z:F1}";
            importantObjects.Add($"x方向に{chairXStr}、z方向に{chairZStr}にChairArea");
        }
        
        // DaiArea（X=0.02, Z=3.55）の位置情報
        Vector3 daiAreaPos = new Vector3(0.02f, playerPos.y, 3.55f);
        float daiAreaDistance = Vector3.Distance(playerPos, daiAreaPos);
        
        // 一定範囲内にいる場合のみ表示（20メートル以内）
        if (daiAreaDistance <= 20.0f)
        {
            Vector3 daiAreaDiff = daiAreaPos - playerPos;
            string daiXStr = daiAreaDiff.x >= 0 ? $"+{daiAreaDiff.x:F1}" : $"{daiAreaDiff.x:F1}";
            string daiZStr = daiAreaDiff.z >= 0 ? $"+{daiAreaDiff.z:F1}" : $"{daiAreaDiff.z:F1}";
            importantObjects.Add($"x方向に{daiXStr}、z方向に{daiZStr}にDaiArea");
        }
    }

    private string GetDirectionText(Vector3 direction)
    {
        // より正確な座標差分表記
        float x = direction.x;
        float z = direction.z;
        
        // 主要な方向を判定
        if (Mathf.Abs(x) > Mathf.Abs(z))
        {
            // X方向が主要
            if (x > 0)
                return z > 0.1f ? "+X+Z" : z < -0.1f ? "+X-Z" : "+X";
            else
                return z > 0.1f ? "-X+Z" : z < -0.1f ? "-X-Z" : "-X";
        }
        else
        {
            // Z方向が主要
            if (z > 0)
                return x > 0.1f ? "+X+Z" : x < -0.1f ? "-X+Z" : "+Z";
            else
                return x > 0.1f ? "+X-Z" : x < -0.1f ? "-X-Z" : "-Z";
        }
    }

    /// <summary>
    /// オブジェクトの種類に応じた数量表現を取得
    /// </summary>
    private string GetCountText(string objectType, int count)
    {
        switch (objectType)
        {
            case "椅子":
                return count == 1 ? "椅子" : $"椅子{count}脚";
            case "テーブル":
                return count == 1 ? "テーブル" : $"テーブル{count}台";
            case "パソコン":
            case "PC":
                return count == 1 ? "パソコン" : $"パソコン{count}台";
            case "テレビ":
                return count == 1 ? "テレビ" : $"テレビ{count}台";
            case "台":
                return count == 1 ? "台" : $"台{count}台";
            default:
                return count == 1 ? objectType : $"{objectType}{count}個";
        }
    }

    /// <summary>
    /// テーブル名から説明を取得
    /// </summary>
    private string GetTableDescription(string tableName)
    {
        switch (tableName)
        {
            case "Table_NW":
                return "北西テーブル";
            case "Table_SE":
                return "南東テーブル";
            case "Table_SW":
                return "南西テーブル";
            case "Table_NE":
                return "北東テーブル";
            default:
                return "テーブル";
        }
    }
    #endregion
    #endregion

    #region 7. デバッグ用メソッド
    void OnDrawGizmosSelected()
    {
        // エディタで検出範囲を表示
        Gizmos.color = Color.blue;
        Gizmos.DrawWireSphere(transform.position, detectionRadius);
        
        // 前方検出の可視化
        if (playerCamera != null)
        {
            Gizmos.color = Color.red;
            Gizmos.DrawRay(playerCamera.transform.position, playerCamera.transform.forward * forwardRayDistance);
        }
        
        // ドロップ位置の予測を表示
        if (interactionController != null && interactionController.CarriedItem != null)
        {
            // 胸元位置の真下に予測ドロップ位置を表示
            Vector3 carryPosition = interactionController.CarriedItem.transform.position;
            Vector3 dropPosition = new Vector3(carryPosition.x, transform.position.y, carryPosition.z);
            
            Gizmos.color = Color.green;
            Gizmos.DrawWireCube(dropPosition, Vector3.one * 0.2f);
            
            // ドロップ位置から下方向のレイ
            Gizmos.color = Color.yellow;
            Gizmos.DrawRay(dropPosition + Vector3.up * 2f, Vector3.down * 4f);
        }
        
        // 移動可能な方向を表示
        Vector3[] directions = {
            Vector3.forward,  // 北
            Vector3.right,    // 東
            Vector3.back,     // 南
            Vector3.left      // 西
        };
        
        Vector3 rayOrigin = transform.position + Vector3.up * 0.5f;
        float checkDistance = 1.5f;
        
        for (int i = 0; i < directions.Length; i++)
        {
            bool canMove = CanMoveInDirection(directions[i]);
            Gizmos.color = canMove ? Color.green : Color.red;
            Gizmos.DrawRay(rayOrigin, directions[i] * checkDistance);
        }
    }
    #endregion
}