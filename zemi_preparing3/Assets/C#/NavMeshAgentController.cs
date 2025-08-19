// NavMeshAgentController - AI専用自動経路探索システム
// AI専用の座標指定移動。障害物を自動回避して目的地に到達
// 構成: 1=Core, 2=Public API, 3=Navigation制御, 4=Animation, 5=Utility

// 必須設定（Unity Editor）：
// - Window > AI > Navigation でNavMesh Bake
// - 床を Navigation Static + Walkable に設定
// - 壁・テーブルを Navigation Static + Not Walkable に設定

// オプション設定：
// - 運搬可能オブジェクトに DynamicNavMeshObstacle 追加
// - Bake設定の調整（Agent Radius: 0.5, Step Height: 0.4）

using UnityEngine;
using UnityEngine.AI;
using System.Collections;
using StarterAssets;

public class NavMeshAgentController : MonoBehaviour
{
    [Header("NavMesh Settings")]
    [Tooltip("Movement speed when navigating to target")]
    public float navigationSpeed = 3.5f;
    
    [Tooltip("Stopping distance from target")]
    public float stoppingDistance = 0.5f;
    
    [Tooltip("Rotation speed when navigating")]
    public float rotationSpeed = 120f;
    
    // コンポーネント参照
    private NavMeshAgent _agent;
    private ThirdPersonController _thirdPersonController;
    private Animator _animator;
    
    // 状態管理
    private bool _isNavigating = false;
    private Vector3 _targetPosition;
    
    // アニメーションID（パフォーマンス最適化）
    private int _animIDSpeed;
    private int _animIDMotionSpeed;

    #region 1. Core Lifecycle
    void Start()
    {
        // コンポーネント取得
        _agent = GetComponent<NavMeshAgent>();
        _thirdPersonController = GetComponent<ThirdPersonController>();
        _animator = GetComponent<Animator>();
        
        // NavMeshAgentが存在しない場合は追加
        if (_agent == null)
        {
            _agent = gameObject.AddComponent<NavMeshAgent>();
        }
        
        // NavMeshAgent設定
        ConfigureAgent();
        
        // アニメーションIDキャッシュ
        _animIDSpeed = Animator.StringToHash("Speed");
        _animIDMotionSpeed = Animator.StringToHash("MotionSpeed");
        
        // 初期状態は無効
        _agent.enabled = false;
    }
    
    void Update()
    {
        if (_isNavigating && _agent.enabled)
        {
            UpdateNavigation();
        }
    }
    #endregion

    #region 2. Public API
    /// <summary>
    /// 指定座標への移動を開始（CommandExecutorから呼ばれる）
    /// </summary>
    public void NavigateToPosition(float x, float y, float z)
    {
        NavigateToPosition(new Vector3(x, y, z));
    }
    
    /// <summary>
    /// Vector3での移動開始
    /// </summary>
    public void NavigateToPosition(Vector3 targetPosition)
    {
        _targetPosition = targetPosition;
        StartNavigation();
    }
    
    /// <summary>
    /// 移動を停止
    /// </summary>
    public void StopNavigation()
    {
        _isNavigating = false;
        
        // NavMeshAgentを無効化
        if (_agent != null && _agent.enabled)
        {
            _agent.ResetPath();
            _agent.enabled = false;
        }
        
        // ThirdPersonControllerを再有効化（人間操作に戻す）
        if (_thirdPersonController != null)
        {
            _thirdPersonController.enabled = true;
        }
        
        // アニメーション停止
        StopMovementAnimation();
        
        Debug.Log("[NavMeshAgent] Navigation stopped");
    }
    
    /// <summary>
    /// 現在移動中かどうか
    /// </summary>
    public bool IsNavigating()
    {
        return _isNavigating;
    }
    
    /// <summary>
    /// 目的地までの残り距離
    /// </summary>
    public float GetRemainingDistance()
    {
        if (_agent != null && _agent.enabled && _agent.hasPath)
        {
            return _agent.remainingDistance;
        }
        return 0f;
    }
    #endregion

    #region 3. Navigation Control
    /// <summary>
    /// ナビゲーション開始処理
    /// </summary>
    private void StartNavigation()
    {
        // ThirdPersonControllerを無効化（AI制御に切り替え）
        if (_thirdPersonController != null)
        {
            _thirdPersonController.enabled = false;
        }
        
        // NavMeshAgent有効化
        _agent.enabled = true;
        _isNavigating = true;
        
        // NavMesh上の有効な位置を探して移動開始
        if (NavMesh.SamplePosition(_targetPosition, out NavMeshHit hit, 5.0f, NavMesh.AllAreas))
        {
            _agent.SetDestination(hit.position);
            Debug.Log($"[NavMeshAgent] Navigating to position: {hit.position}");
        }
        else
        {
            Debug.LogWarning($"[NavMeshAgent] Target position {_targetPosition} is not on NavMesh");
            StopNavigation();
        }
    }
    
    /// <summary>
    /// ナビゲーション状態の更新（毎フレーム）
    /// </summary>
    private void UpdateNavigation()
    {
        // 到着判定
        if (!_agent.pathPending && _agent.remainingDistance <= _agent.stoppingDistance)
        {
            if (!_agent.hasPath || _agent.velocity.sqrMagnitude == 0f)
            {
                StopNavigation();
                return;
            }
        }
        
        // アニメーション更新
        UpdateMovementAnimation();
    }
    
    /// <summary>
    /// NavMeshAgentの初期設定
    /// </summary>
    private void ConfigureAgent()
    {
        _agent.speed = navigationSpeed;
        _agent.stoppingDistance = stoppingDistance;
        _agent.angularSpeed = rotationSpeed;
        
        // その他の推奨設定
        _agent.acceleration = 8f;        // 加速度
        _agent.autoBraking = true;       // 自動ブレーキ
        _agent.autoRepath = true;        // 自動経路再計算
    }
    #endregion

    #region 4. Animation Control
    /// <summary>
    /// 移動アニメーションの更新
    /// </summary>
    private void UpdateMovementAnimation()
    {
        if (_animator == null) return;
        
        float speed = _agent.velocity.magnitude;
        _animator.SetFloat(_animIDSpeed, speed);
        _animator.SetFloat(_animIDMotionSpeed, speed > 0.1f ? 1f : 0f);
    }
    
    /// <summary>
    /// 移動アニメーションの停止
    /// </summary>
    private void StopMovementAnimation()
    {
        if (_animator == null) return;
        
        _animator.SetFloat(_animIDSpeed, 0f);
        _animator.SetFloat(_animIDMotionSpeed, 0f);
    }
    #endregion

    #region 5. Debug & Utility
    /// <summary>
    /// デバッグ用：経路を可視化
    /// </summary>
    void OnDrawGizmosSelected()
    {
        if (_agent != null && _agent.enabled && _agent.hasPath)
        {
            // 現在の経路を緑線で表示
            Gizmos.color = Color.green;
            var corners = _agent.path.corners;
            
            for (int i = 0; i < corners.Length - 1; i++)
            {
                Gizmos.DrawLine(corners[i], corners[i + 1]);
            }
            
            // 目的地を赤い球で表示
            if (corners.Length > 0)
            {
                Gizmos.color = Color.red;
                Gizmos.DrawSphere(corners[corners.Length - 1], 0.3f);
            }
        }
        
        // 停止距離を黄色い円で表示
        if (_isNavigating && _agent != null)
        {
            Gizmos.color = Color.yellow;
            Gizmos.DrawWireSphere(transform.position, stoppingDistance);
        }
    }
    #endregion
}