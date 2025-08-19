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
    
    [Header("Narrator Settings")]
    public float updateInterval = 2.0f; // ナレーション更新間隔（秒）
    public bool enablePositionNarration = true;
    public bool enableObjectNarration = true;
    public bool enableDirectionNarration = true;
    public bool enableActionNarration = true; // アクションナレーションの有効/無効
    public bool suppressTechnicalLogs = true; // 技術的ログを非表示にする
    
    private Camera playerCamera;
    private PlayerPickupController pickupController;
    private Vector3 lastPosition;
    private float lastUpdateTime;
    private Dictionary<string, Vector3> lastKnownObjectPositions = new Dictionary<string, Vector3>();
    
    // シングルトンインスタンス
    public static AccessibilityNarrator Instance;
    
    // 前回の近くのオブジェクト（重複通知を避けるため）
    private string lastNearbyItem = "";
    private string lastNearbyTV = "";
    
    // 前回の状況報告内容（変化があった場合のみ出力するため）
    private string lastSituationReport = "";
    
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
    
    void Start()
    {
        // プレイヤーのカメラを取得
        playerCamera = Camera.main;
        if (playerCamera == null)
        {
            playerCamera = FindFirstObjectByType<Camera>();
        }
        
        // プレイヤーのPickupControllerを取得
        pickupController = GetComponent<PlayerPickupController>();
        
        lastPosition = transform.position;
        lastUpdateTime = Time.time;
        
        // 初期ナレーション（強制的に出力）
        lastSituationReport = ""; // 初期状況を確実に出力するため
        NarrateCurrentSituation();
    }
    
    void Update()
    {
        // 定期的にナレーションを更新
        if (Time.time - lastUpdateTime >= updateInterval)
        {
            NarrateCurrentSituation();
            lastUpdateTime = Time.time;
        }
        
        // 移動時のナレーション（簡潔に）
        if (Vector3.Distance(transform.position, lastPosition) > 2.0f)
        {
            NarrateMovement();
            lastPosition = transform.position;
        }
    }
    
    public void NarrateCurrentSituation()
    {
        if (!enablePositionNarration && !enableObjectNarration) return;
        
        System.Text.StringBuilder narration = new System.Text.StringBuilder();
        
        // 現在の状況タイトル
        narration.AppendLine("[Narrator] === 現在の状況 ===");
        
        // 現在地情報
        narration.AppendLine("[現在地]");
        Vector3 pos = transform.position;
        narration.AppendLine($"座標（X={pos.x:F1}, Z={pos.z:F1}）");
        
        // 向いている方向
        string currentDirection = GetDirectionText(transform.forward);
        narration.AppendLine($"{currentDirection}方向を向いています");
        
        // 周辺の状況
        narration.AppendLine("[周辺の状況]");
        var objects = GetImportantObjectsPositions();
        var tables = GetTablePositions();
        
        var allObjects = new List<string>();
        allObjects.AddRange(objects);
        allObjects.AddRange(tables);
        
        if (allObjects.Count > 0)
        {
            foreach (var obj in allObjects)
            {
                narration.AppendLine(obj);
            }
        }
        else
            {
            narration.AppendLine("周辺に重要なオブジェクトはありません");
        }
        
        // 持っているもの
        narration.AppendLine("[持っているもの]");
        if (pickupController != null && pickupController.carriedItem != null)
        {
            narration.AppendLine(pickupController.carriedItem.itemName);
        }
        else
        {
            narration.AppendLine("何も持っていません");
        }
        

        
        // 可能なコマンド
        narration.AppendLine("[可能なコマンド]");
        
        // 移動可能な方向のみを取得
        List<string> commands = GetAvailableMovementCommands();
        
        // アイテム関連のコマンド（何も持っていない場合のみ）
        if (pickupController != null && pickupController.currentNearbyItem != null && pickupController.carriedItem == null)
        {
            string itemName = pickupController.currentNearbyItem.itemName;
            // 「Dai」を「PCプレート」として表示
            if (itemName == "Dai")
            {
                itemName = "PCプレート";
            }
            commands.Add($"pickup（{itemName}を拾う）");
        }
        
        // ドロップコマンド
        if (pickupController != null && pickupController.carriedItem != null)
        {
            string dropInfo = GetDropLocationInfo();
            commands.Add(dropInfo);
        }
        
        // TV操作コマンド
        if (pickupController != null && pickupController.currentNearbyTV != null)
        {
            string tvState = pickupController.currentNearbyTV.IsOn() ? "ON" : "OFF";
            commands.Add($"interact（{pickupController.currentNearbyTV.deviceName}を操作・現在{tvState}）");
        }
        
        // コマンドを出力
        if (commands.Count > 0)
        {
        narration.AppendLine($"  {string.Join("、", commands)}");
        }
        else
        {
            narration.AppendLine("  移動不可");
        }
        
        narration.AppendLine("========================");
        
        // 前回と同じ内容かチェック
        string currentReport = narration.ToString();
        if (lastSituationReport == currentReport)
        {
            return; // 同じ内容の場合は出力しない
        }
        
        // 前回の内容を更新
        lastSituationReport = currentReport;
        
        // 構造化されたログを出力
        Debug.Log(currentReport);
        
        // 完了通知を即座に送信
        OnCommandCompleted();
    }
    
    private IEnumerator NotifyCommandCompletionAfterDelay()
    {
        yield return new WaitForSeconds(0.1f); // 短い待機
        OnCommandCompleted();
    }
    
    void NarrateMovement()
    {
        if (!enableDirectionNarration) return;
        
        Vector3 direction = (transform.position - lastPosition).normalized;
        string directionText = GetDirectionText(direction);
        Vector3 pos = transform.position;
        
        // 移動距離の差分を計算
        float moveDistance = Vector3.Distance(transform.position, lastPosition);
        Vector3 positionDiff = transform.position - lastPosition;
        
        Debug.Log($"[Narrator] {directionText}方向に約{moveDistance:F1}メートル移動（X:{positionDiff.x:+0.0;-0.0}, Z:{positionDiff.z:+0.0;-0.0}）現在座標X:{pos.x:F1}, Z:{pos.z:F1}");
    }
    
    string GetPositionDescription()
    {
        Vector3 pos = transform.position;
        
        // 詳細な位置説明
        string roomDescription = "";
        
        if (pos.x > 0 && pos.z > 0)
            roomDescription = "部屋の北東側";
        else if (pos.x > 0 && pos.z < 0)
            roomDescription = "部屋の南東側";
        else if (pos.x < 0 && pos.z > 0)
            roomDescription = "部屋の北西側";
        else if (pos.x < 0 && pos.z < 0)
            roomDescription = "部屋の南西側";
        else if (pos.x > 0)
            roomDescription = "部屋の東側";
        else if (pos.x < 0)
            roomDescription = "部屋の西側";
        else if (pos.z > 0)
            roomDescription = "部屋の北側";
        else if (pos.z < 0)
            roomDescription = "部屋の南側";
        else
            roomDescription = "部屋の中央";
        
        // 向いている方向を追加
        Vector3 forward = transform.forward;
        string facingDirection = GetDirectionText(forward);
        
        // 座標情報を追加
        string coordinates = $"座標X:{pos.x:F1}, Z:{pos.z:F1}";
        
        return $"現在{roomDescription}にいます（{coordinates}）。{facingDirection}を向いています";
    }
    
    string GetObjectInFront()
    {
        if (playerCamera == null) return "";
        
        RaycastHit hit;
        Vector3 rayOrigin = playerCamera.transform.position;
        Vector3 rayDirection = playerCamera.transform.forward;
        
        if (Physics.Raycast(rayOrigin, rayDirection, out hit, forwardRayDistance, detectionLayer))
        {
            return GetObjectDescription(hit.collider.gameObject);
        }
        
        return "";
    }
    
    (string, float) GetObjectInFrontWithDistance()
    {
        if (playerCamera == null) return ("", 0f);
        
        RaycastHit hit;
        Vector3 rayOrigin = playerCamera.transform.position;
        Vector3 rayDirection = playerCamera.transform.forward;
        
        if (Physics.Raycast(rayOrigin, rayDirection, out hit, forwardRayDistance, detectionLayer))
        {
            // デバッグ情報
            Debug.Log($"[Debug] レイキャストヒット: {hit.collider.gameObject.name}");
            
            string objDescription = GetObjectDescriptionWithObstacles(hit.collider.gameObject);
            
            Debug.Log($"[Debug] 前方オブジェクト検出結果: '{objDescription}'");
            
            if (!string.IsNullOrEmpty(objDescription))
            {
                return (objDescription, hit.distance);
            }
        }
        
        return ("", 0f);
    }
    
    List<string> GetSurroundingObjects()
    {
        List<string> objects = new List<string>();
        Collider[] colliders = Physics.OverlapSphere(transform.position, detectionRadius, detectionLayer);
        
        Dictionary<string, List<Vector3>> objectGroups = new Dictionary<string, List<Vector3>>();
        
        foreach (Collider col in colliders)
        {
            if (col.gameObject == gameObject) continue; // 自分自身は除外
            
            string objName = GetObjectDescription(col.gameObject);
            if (!string.IsNullOrEmpty(objName))
            {
                // 重要なオブジェクトは除外（すでに重要なオブジェクトセクションで表示されるため）
                if (IsImportantObject(objName)) continue;
                
                if (!objectGroups.ContainsKey(objName))
                {
                    objectGroups[objName] = new List<Vector3>();
                }
                objectGroups[objName].Add(col.transform.position);
            }
        }
        
        foreach (var group in objectGroups)
        {
            string objName = group.Key;
            List<Vector3> positions = group.Value;
            
            if (positions.Count == 1)
            {
                Vector3 diff = positions[0] - transform.position;
                string directionText = GetDirectionText(diff.normalized);
                string coordinates = $"X:{diff.x:+0.0;-0.0}, Z:{diff.z:+0.0;-0.0}";
                objects.Add($"{directionText}({coordinates})に{objName}");
            }
            else
            {
                // 複数ある場合は、最も近いものの方向と距離を表示
                Vector3 nearest = positions.OrderBy(p => Vector3.Distance(transform.position, p)).First();
                Vector3 diff = nearest - transform.position;
                string directionText = GetDirectionText(diff.normalized);
                string coordinates = $"X:{diff.x:+0.0;-0.0}, Z:{diff.z:+0.0;-0.0}";
                string countText = GetCountText(objName, positions.Count);
                objects.Add($"{directionText}({coordinates})に{countText}");
            }
        }
        
        return objects.Take(5).ToList(); // 最大5個まで
    }
    
    /// <summary>
    /// 重要なオブジェクトかどうかを判定
    /// </summary>
    private bool IsImportantObject(string objName)
    {
        return objName == "椅子" || objName == "運搬可能な椅子" || objName == "テレビ" || 
               objName == "パソコン" || objName == "台" || objName == "テーブル";
    }
    
    string GetObjectDescription(GameObject obj)
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
    string GetObjectDescriptionWithObstacles(GameObject obj)
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
    
    string GetDirectionText(Vector3 direction)
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
    
    string GetInteractableObjectsInfo()
    {
        List<string> interactableInfo = new List<string>();
        
        // 近くのアイテム（拾える）
        if (pickupController != null && pickupController.currentNearbyItem != null)
        {
            string itemName = pickupController.currentNearbyItem.itemName;
            // 「Dai」を「PCプレート」として表示
            if (itemName == "Dai")
            {
                itemName = "PCプレート";
            }
            interactableInfo.Add($"pickup（{itemName}を拾う）");
        }
        
        // 近くのTV（操作できる）
        if (pickupController != null && pickupController.currentNearbyTV != null)
        {
            string tvState = pickupController.currentNearbyTV.IsOn() ? "ON" : "OFF";
            interactableInfo.Add($"interact（TVを操作・現在{tvState}）");
        }
        
        return string.Join("。", interactableInfo);
    }
    
    string GetDropLocationInfo()
    {
        if (playerCamera == null) return "pickup（目の前に置く）";
        
        // プレイヤーの前方1.5メートルの位置を基準とする
        Vector3 dropPosition = transform.position + transform.forward * 1.5f;
        
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
    
    string GetSurfaceType(GameObject surface)
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
    
    string CheckSurfaceTypeName(GameObject obj)
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
    
    // === イベントハンドラーメソッド ===
    
    /// <summary>
    /// アイテムを拾った時のナレーション
    /// </summary>
    public void OnItemPickedUp(string itemName)
    {
        if (!enableActionNarration) return;
        
        // 「Dai」を「PCプレート」として表示
        string displayName = itemName;
        if (itemName == "Dai")
        {
            displayName = "PCプレート";
        }
        
        Debug.Log($"[Narrator] {displayName}を持ち上げました！pickupコマンドで置くことができます。");
    }
    
    /// <summary>
    /// アイテムを置いた時のナレーション
    /// </summary>
    public void OnItemDropped(string itemName, Vector3 dropPosition)
    {
        if (!enableActionNarration) return;
        
        // ドロップした場所の詳細を取得
        string dropLocationDetails = GetDropLocationDetails(dropPosition);
        
        // 「Dai」を「PCプレート」として表示
        string displayName = itemName;
        if (itemName == "Dai")
        {
            displayName = "PCプレート";
        }
        
        Debug.Log($"[Narrator] {displayName}を置きました！場所: {dropLocationDetails}");
    }
    
    /// <summary>
    /// 近くのアイテムを検出した時のナレーション
    /// </summary>
    public void OnNearbyItemDetected(string itemName, float distance)
    {
        if (!enableActionNarration) return;
        
        // 重複を避ける
        string currentItem = $"{itemName}_{distance:F1}";
        if (lastNearbyItem == currentItem) return;
        lastNearbyItem = currentItem;
        
        // 方角を計算
        ItemPickup nearbyItem = pickupController.currentNearbyItem;
        string direction = "";
        if (nearbyItem != null)
        {
            Vector3 directionVector = (nearbyItem.transform.position - transform.position).normalized;
            direction = GetDirectionText(directionVector);
        }
        
        // 「Dai」を「PCプレート」として表示
        string displayName = itemName;
        if (itemName == "Dai")
        {
            displayName = "PCプレート";
        }
        
        Debug.Log($"[Narrator] {direction}約{distance:F1}メートルに{displayName}があります・pickupコマンドで持ち上げられます");
    }
    
    /// <summary>
    /// TVを操作した時のナレーション
    /// </summary>
    public void OnTVToggled(string deviceName, bool isOn)
    {
        if (!enableActionNarration) return;
        
        string stateText = isOn ? "ON" : "OFF";
        Debug.Log($"[Narrator] {deviceName}を{stateText}にしました！");
    }
    
    /// <summary>
    /// 近くのTVを検出した時のナレーション
    /// </summary>
    public void OnNearbyTVDetected(string deviceName, float distance, bool isOn)
    {
        if (!enableActionNarration) return;
        
        // 重複を避ける
        string stateText = isOn ? "ON" : "OFF";
        string currentTV = $"{deviceName}_{distance:F1}_{stateText}";
        if (lastNearbyTV == currentTV) return;
        lastNearbyTV = currentTV;
        
        // 方角を計算
        TVInteract nearbyTV = pickupController.currentNearbyTV;
        string direction = "";
        if (nearbyTV != null)
        {
            Vector3 directionVector = (nearbyTV.GetButtonPosition() - transform.position).normalized;
            direction = GetDirectionText(directionVector);
        }
        
        Debug.Log($"[Narrator] {direction}約{distance:F1}メートルに{deviceName}があります・現在{stateText}・interactコマンドで操作できます");
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
    /// 近くのアイテムリセット
    /// </summary>
    public void ResetNearbyItem()
    {
        lastNearbyItem = "";
    }
    
    /// <summary>
    /// 近くのTVリセット
    /// </summary>
    public void ResetNearbyTV()
    {
        lastNearbyTV = "";
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
                    
                    // 座標表示が正常に動作することを確認済み
                    
                    // 座標表示を確実に修正
                    string xStr = diff.x >= 0 ? $"+{diff.x:F1}" : $"{diff.x:F1}";
                    string zStr = diff.z >= 0 ? $"+{diff.z:F1}" : $"{diff.z:F1}";
                    // 台をPCプレートとして送信
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
                    
                    // 座標表示が正常に動作することを確認済み
                    
                    // 座標表示を確実に修正
                    string xStr = diff.x >= 0 ? $"+{diff.x:F1}" : $"{diff.x:F1}";
                    string zStr = diff.z >= 0 ? $"+{diff.z:F1}" : $"{diff.z:F1}";
                    // 台をPCプレートとして送信
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
    /// 周辺のテーブルの位置を取得（2メートル範囲）
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
    
    // コマンド実行完了を通知するメソッド
    public void OnCommandCompleted()
    {
        // コマンド実行完了をログに出力
        Debug.Log("[Narrator] コマンド実行完了");
        
        // エリア到達チェック（移動後に特定エリアに到達したかを確認）
        CheckAreaArrival();
        
        // LLMCommunicatorに通知
        if (LLMCommunicator.Instance != null)
        {
            LLMCommunicator.Instance.OnCommandCompleted();
        }
    }
    
    /// <summary>
    /// プレイヤーが特定エリアに到達した際のメッセージ出力
    /// </summary>
    public void CheckAreaArrival()
    {
        if (!enableActionNarration) return;
        
        Vector3 currentPosition = transform.position;
        
        // 持っているアイテムを確認
        PlayerPickupController pickup = GetComponent<PlayerPickupController>();
        bool hasItem = pickup != null && pickup.carriedItem != null;
        string heldItemName = hasItem ? pickup.carriedItem.itemName : "";
        
        // ChairArea到達チェック（椅子を持っている場合）
        if (heldItemName.Contains("Chair") || heldItemName.Contains("椅子"))
        {
            Vector3 chairAreaCenter = new Vector3(5.48f, currentPosition.y, -3.69f);
            float chairAreaDistance = Vector3.Distance(currentPosition, chairAreaCenter);
            if (chairAreaDistance <= 2.5f)
            {
                Debug.Log("[Narrator] ChairAreaに到達しました。椅子を置く準備が完了しました。");
            }
        }
        
        // ChairArea到達チェック（椅子を置いた後、何も持っていない場合）
        if (string.IsNullOrEmpty(heldItemName))
        {
            Vector3 chairAreaCenter = new Vector3(5.48f, currentPosition.y, -3.69f);
            float chairAreaDistance = Vector3.Distance(currentPosition, chairAreaCenter);
            if (chairAreaDistance <= 2.5f)
            {
                Debug.Log("[Narrator] ChairAreaに到達しました。椅子を置く作業が完了しました。");
            }
        }
        
        // PCプレートに近づいた時のチェック（何も持っていない場合）
        if (string.IsNullOrEmpty(heldItemName))
        {
            // PCプレート（Dai）の位置を確認
            if (pickupController != null && pickupController.currentNearbyItem != null && pickupController.currentNearbyItem.itemName == "Dai")
            {
                float plateDistance = Vector3.Distance(currentPosition, pickupController.currentNearbyItem.transform.position);
                if (plateDistance <= 2.5f)
                {
                    Debug.Log("[Narrator] PCプレートに到達しました。PCプレートを拾う準備が完了しました。");
                }
            }
        }
        
        // DaiArea到達チェック（PCプレートを持っている場合）
        if (heldItemName.Contains("Plate") || heldItemName.Contains("プレート"))
        {
            Vector3 daiAreaCenter = new Vector3(0.02f, currentPosition.y, 3.55f);
            float daiAreaDistance = Vector3.Distance(currentPosition, daiAreaCenter);
            if (daiAreaDistance <= 2.5f)
            {
                Debug.Log("[Narrator] DaiAreaに到達しました。PCプレートを置く準備が完了しました。");
            }
        }
        
        // プレート上到達チェック（PCを持っている場合）
        if (heldItemName.Contains("PC") || heldItemName.Contains("パソコン") || heldItemName.Contains("Computer"))
        {
            Vector3 daiAreaCenter = new Vector3(0.02f, currentPosition.y, 3.55f);
            float plateDistance = Vector3.Distance(currentPosition, daiAreaCenter);
            if (plateDistance <= 2.0f)
            {
                Debug.Log("[Narrator] PCプレートの上に到達しました。PCを置く準備が完了しました。");
            }
        }
        
        // DaiArea到達チェック（PCプレートを置いた後、何も持っていない場合）
        if (string.IsNullOrEmpty(heldItemName))
        {
            Vector3 daiAreaCenter = new Vector3(0.02f, currentPosition.y, 3.55f);
            float daiAreaDistance = Vector3.Distance(currentPosition, daiAreaCenter);
            if (daiAreaDistance <= 2.5f)
            {
                Debug.Log("[Narrator] DaiAreaに到達しました。PCプレートを置く作業が完了しました。");
            }
        }
    }
    
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
        if (pickupController != null && pickupController.carriedItem != null)
        {
            Vector3 dropPosition = transform.position + transform.forward * 1.5f;
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
} 