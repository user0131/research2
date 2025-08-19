// DynamicNavMeshObstacle - 動的NavMesh障害物制御システム
// ItemPickupと連携して、持ち上げ時に自動的にNavMeshを更新
// 椅子、PC、台など、どんなオブジェクトにも適用可能
// 構成: 1=Core, 2=障害物制御, 3=サイズ検出, 4=状態管理, 5=デバッグ
//
// 使用方法:
//   1. 椅子オブジェクトを選択
//   2. Add Component → ItemPickup
//   3. Add Component → DynamicNavMeshObstacle
//   4. NavMeshObstacle（自動追加される）
//   5. Auto Detect Size = ON

using UnityEngine;
using UnityEngine.AI;

[RequireComponent(typeof(NavMeshObstacle))]
public class DynamicNavMeshObstacle : MonoBehaviour
{
    [Header("Settings")]
    [Tooltip("Colliderから自動的にサイズを取得")]
    public bool autoDetectSize = true;
    
    [Tooltip("デバッグログを表示")]
    public bool showDebugLogs = false;
    
    // コンポーネント参照
    private NavMeshObstacle _obstacle;
    private ItemPickup _itemPickup;
    private Collider _objectCollider;
    
    // 状態管理
    private bool _wasPickedUp = false;
    
    #region 1. Core Lifecycle
    void Start()
    {
        if (!InitializeComponents())
        {
            return; // 初期化失敗時は処理終了
        }
        
        ConfigureObstacle();
        LogInitialization();
    }
    
    void Update()
    {
        MonitorPickupState();
    }
    #endregion
    
    #region 2. 障害物制御システム
    /// <summary>
    /// NavMeshObstacleの初期設定
    /// </summary>
    private void ConfigureObstacle()
    {
        if (_obstacle == null) return;
        
        SetupCarvingMode();
        SetupObstacleSize();
        SetObstacleShape();
    }
    
    /// <summary>
    /// Carvingモードの設定（リアルタイムNavMesh更新）
    /// </summary>
    private void SetupCarvingMode()
    {
        _obstacle.carving = true;
        _obstacle.carvingMoveThreshold = 0.1f;  // 0.1m動いたら更新
        _obstacle.carvingTimeToStationary = 0.5f; // 0.5秒静止で確定
    }
    
    /// <summary>
    /// 障害物サイズの設定
    /// </summary>
    private void SetupObstacleSize()
    {
        if (autoDetectSize && _objectCollider != null)
        {
            DetectAndSetObstacleSize();
        }
    }
    
    /// <summary>
    /// 障害物形状の設定
    /// </summary>
    private void SetObstacleShape()
    {
        _obstacle.shape = NavMeshObstacleShape.Box;
    }
    #endregion
    
    #region 3. サイズ検出システム
    /// <summary>
    /// Colliderからサイズを自動検出して設定
    /// </summary>
    private void DetectAndSetObstacleSize()
    {
        if (_objectCollider == null || _obstacle == null) return;
        
        switch (_objectCollider)
        {
            case BoxCollider box:
                SetBoxColliderSize(box);
                break;
            case SphereCollider sphere:
                SetSphereColliderSize(sphere);
                break;
            case CapsuleCollider capsule:
                SetCapsuleColliderSize(capsule);
                break;
            default:
                SetDefaultColliderSize();
                break;
        }
        
        LogDetectedSize();
    }
    
    /// <summary>
    /// BoxColliderのサイズ設定
    /// </summary>
    private void SetBoxColliderSize(BoxCollider box)
    {
        _obstacle.size = Vector3.Scale(box.size, transform.localScale);
        _obstacle.center = box.center;
    }
    
    /// <summary>
    /// SphereColliderのサイズ設定
    /// </summary>
    private void SetSphereColliderSize(SphereCollider sphere)
    {
        float maxScale = Mathf.Max(transform.localScale.x, transform.localScale.y, transform.localScale.z);
        float diameter = sphere.radius * 2f * maxScale;
        _obstacle.size = new Vector3(diameter, diameter, diameter);
        _obstacle.center = sphere.center;
    }
    
    /// <summary>
    /// CapsuleColliderのサイズ設定
    /// </summary>
    private void SetCapsuleColliderSize(CapsuleCollider capsule)
    {
        float radius = capsule.radius * Mathf.Max(transform.localScale.x, transform.localScale.z);
        float height = capsule.height * transform.localScale.y;
        _obstacle.size = new Vector3(radius * 2f, height, radius * 2f);
        _obstacle.center = capsule.center;
    }
    
    /// <summary>
    /// その他のCollider（MeshCollider等）のサイズ設定
    /// </summary>
    private void SetDefaultColliderSize()
    {
        Bounds bounds = _objectCollider.bounds;
        _obstacle.size = bounds.size;
        _obstacle.center = bounds.center - transform.position;
    }
    #endregion
    
    #region 4. 状態管理システム
    /// <summary>
    /// 持ち上げ状態の監視
    /// </summary>
    private void MonitorPickupState()
    {
        if (_itemPickup == null) return;
        
        bool isCurrentlyPickedUp = _itemPickup.IsPickedUp();
        
        if (isCurrentlyPickedUp != _wasPickedUp)
        {
            OnPickupStateChanged(isCurrentlyPickedUp);
            _wasPickedUp = isCurrentlyPickedUp;
        }
    }
    
    /// <summary>
    /// 持ち上げ状態が変化した時の処理
    /// </summary>
    private void OnPickupStateChanged(bool isPickedUp)
    {
        if (_obstacle == null) return;
        
        // 持ち上げ時は障害物OFF、置いた時はON
        _obstacle.enabled = !isPickedUp;
        
        LogStateChange(isPickedUp);
    }
    #endregion
    
    #region 5. ユーティリティ・デバッグ
    /// <summary>
    /// コンポーネントの初期化
    /// </summary>
    private bool InitializeComponents()
    {
        // コンポーネント取得
        _obstacle = GetComponent<NavMeshObstacle>();
        _itemPickup = GetComponent<ItemPickup>();
        _objectCollider = GetComponent<Collider>();
        
        // ItemPickupがない場合は警告
        if (_itemPickup == null)
        {
            LogWarning("ItemPickup not found");
            enabled = false; // このスクリプトを無効化
            return false;
        }
        
        return true;
    }
    
    /// <summary>
    /// 初期化完了ログ
    /// </summary>
    private void LogInitialization()
    {
        if (showDebugLogs)
        {
            Debug.Log($"[DynamicNavMeshObstacle] Initialized: {gameObject.name}");
        }
    }
    
    /// <summary>
    /// サイズ検出ログ
    /// </summary>
    private void LogDetectedSize()
    {
        if (showDebugLogs && _obstacle != null)
        {
            Debug.Log($"[DynamicNavMeshObstacle] Auto-detected size: {_obstacle.size}");
        }
    }
    
    /// <summary>
    /// 状態変化ログ
    /// </summary>
    private void LogStateChange(bool isPickedUp)
    {
        if (showDebugLogs)
        {
            string status = isPickedUp ? "picked up (obstacle OFF)" : "dropped (obstacle ON)";
            Debug.Log($"[DynamicNavMeshObstacle] {gameObject.name} {status}");
        }
    }
    
    /// <summary>
    /// 警告ログ
    /// </summary>
    private void LogWarning(string message)
    {
        if (showDebugLogs)
        {
            Debug.LogWarning($"[DynamicNavMeshObstacle] {message} on {gameObject.name}");
        }
    }
    
    /// <summary>
    /// デバッグ用：障害物の範囲を可視化
    /// </summary>
    void OnDrawGizmosSelected()
    {
        // NavMeshObstacleの範囲を表示
        NavMeshObstacle obs = _obstacle != null ? _obstacle : GetComponent<NavMeshObstacle>();
        if (obs == null) return;
        
        DrawObstacleGizmo(obs);
    }
    
    /// <summary>
    /// 障害物のGizmo描画
    /// </summary>
    private void DrawObstacleGizmo(NavMeshObstacle obs)
    {
        // 障害物が有効なら赤、無効なら緑
        Gizmos.color = obs.enabled 
            ? new Color(1f, 0f, 0f, 0.3f)  // 赤（障害物）
            : new Color(0f, 1f, 0f, 0.3f); // 緑（通過可能）
        
        Matrix4x4 oldMatrix = Gizmos.matrix;
        Gizmos.matrix = Matrix4x4.TRS(
            transform.position + transform.rotation * obs.center,
            transform.rotation,
            Vector3.one
        );
        
        Gizmos.DrawCube(Vector3.zero, obs.size);
        Gizmos.DrawWireCube(Vector3.zero, obs.size);
        
        Gizmos.matrix = oldMatrix;
    }
    #endregion
}