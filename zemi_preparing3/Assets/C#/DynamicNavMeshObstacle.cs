// 動的NavMesh障害物 - シンプル汎用コンポーネント
// ItemPickupと連携して、持ち上げ時に自動的にNavMeshを更新
// 椅子、PC、台など、どんなオブジェクトにも適用可能
// 使い方
//   // Unity Editorで設定
//   1. 椅子オブジェクトを選択
//   2. Add Component → ItemPickup
//   3. Add Component → DynamicNavMeshObstacle
//   4. Add Component → NavMeshObstacle（自動追加される）
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
    
    private NavMeshObstacle obstacle;
    private ItemPickup itemPickup;
    private Collider objectCollider;
    private bool wasPickedUp = false;
    
    void Start()
    {
        // コンポーネント取得
        obstacle = GetComponent<NavMeshObstacle>();
        itemPickup = GetComponent<ItemPickup>();
        objectCollider = GetComponent<Collider>();
        
        // ItemPickupがない場合は警告
        if (itemPickup == null)
        {
            if (showDebugLogs)
            {
                Debug.LogWarning($"[DynamicNavMeshObstacle] ItemPickup not found on {gameObject.name}");
            }
            enabled = false; // このスクリプトを無効化
            return;
        }
        
        // NavMeshObstacleの設定
        ConfigureObstacle();
        
        if (showDebugLogs)
        {
            Debug.Log($"[DynamicNavMeshObstacle] Initialized: {gameObject.name}");
        }
    }
    
    void Update()
    {
        if (itemPickup == null) return;
        
        // 持ち上げ状態の変化を監視
        bool isCurrentlyPickedUp = itemPickup.IsPickedUp();
        
        if (isCurrentlyPickedUp != wasPickedUp)
        {
            OnPickupStateChanged(isCurrentlyPickedUp);
            wasPickedUp = isCurrentlyPickedUp;
        }
    }
    
    /// <summary>
    /// NavMeshObstacleの初期設定
    /// </summary>
    private void ConfigureObstacle()
    {
        if (obstacle == null) return;
        
        // Carvingモード設定（リアルタイムNavMesh更新）
        obstacle.carving = true;
        obstacle.carvingMoveThreshold = 0.1f;  // 0.1m動いたら更新
        obstacle.carvingTimeToStationary = 0.5f; // 0.5秒静止で確定
        
        // サイズの自動検出
        if (autoDetectSize && objectCollider != null)
        {
            DetectAndSetObstacleSize();
        }
        
        // 形状はBoxで固定
        obstacle.shape = NavMeshObstacleShape.Box;
    }
    
    /// <summary>
    /// Colliderからサイズを自動検出して設定
    /// </summary>
    private void DetectAndSetObstacleSize()
    {
        if (objectCollider == null || obstacle == null) return;
        
        // BoxColliderの場合
        if (objectCollider is BoxCollider box)
        {
            obstacle.size = Vector3.Scale(box.size, transform.localScale);
            obstacle.center = box.center;
        }
        // SphereColliderの場合
        else if (objectCollider is SphereCollider sphere)
        {
            float diameter = sphere.radius * 2f * Mathf.Max(transform.localScale.x, transform.localScale.y, transform.localScale.z);
            obstacle.size = new Vector3(diameter, diameter, diameter);
            obstacle.center = sphere.center;
        }
        // CapsuleColliderの場合
        else if (objectCollider is CapsuleCollider capsule)
        {
            float radius = capsule.radius * Mathf.Max(transform.localScale.x, transform.localScale.z);
            float height = capsule.height * transform.localScale.y;
            obstacle.size = new Vector3(radius * 2f, height, radius * 2f);
            obstacle.center = capsule.center;
        }
        // その他（MeshCollider等）
        else
        {
            Bounds bounds = objectCollider.bounds;
            obstacle.size = bounds.size;
            obstacle.center = bounds.center - transform.position;
        }
        
        if (showDebugLogs)
        {
            Debug.Log($"[DynamicNavMeshObstacle] Auto-detected size: {obstacle.size}");
        }
    }
    
    /// <summary>
    /// 持ち上げ状態が変化した時の処理
    /// </summary>
    private void OnPickupStateChanged(bool isPickedUp)
    {
        if (obstacle == null) return;
        
        // 持ち上げ時は障害物OFF、置いた時はON
        obstacle.enabled = !isPickedUp;
        
        if (showDebugLogs)
        {
            string status = isPickedUp ? "picked up (obstacle OFF)" : "dropped (obstacle ON)";
            Debug.Log($"[DynamicNavMeshObstacle] {gameObject.name} {status}");
        }
    }
    
    /// <summary>
    /// デバッグ用：障害物の範囲を可視化
    /// </summary>
    void OnDrawGizmosSelected()
    {
        // NavMeshObstacleの範囲を表示
        NavMeshObstacle obs = obstacle != null ? obstacle : GetComponent<NavMeshObstacle>();
        if (obs != null)
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
    }
}