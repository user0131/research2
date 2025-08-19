// ItemPickup - 拾い上げ可能アイテム制御コンポーネント
// アイテムの物理的挙動（持ち上げ・設置）を制御
// 構成: 1=Core, 2=Public API, 3=物理制御, 4=状態管理

using UnityEngine;

public class ItemPickup : MonoBehaviour
{
    [Header("Item Settings")]
    public string itemName = "PC";
    
    [Header("Carry Position")]
    [Tooltip("持ち上げ時のローカル位置")]
    public Vector3 carryOffset = new Vector3(0, 0.1f, 0.1f);
    
    [Header("Physics")]
    public bool usePhysics = true;
    
    // コンポーネント参照
    private Rigidbody _rigidbody;
    private Collider _collider;
    
    // 状態管理
    private bool _isPickedUp = false;
    
    #region 1. Core Lifecycle
    void Start()
    {
        InitializeComponents();
    }
    #endregion
    
    #region 2. Public API
    /// <summary>
    /// アイテムを持ち上げる（PlayerInteractionControllerから呼ばれる）
    /// </summary>
    public void PickUp(Transform parent)
    {
        if (_isPickedUp || parent == null) return;
        
        _isPickedUp = true;
        
        SetupParentRelation(parent);
        DisablePhysics();
        DisableCollision();
        SetCarryPosition();
    }
    
    /// <summary>
    /// アイテムを設置する（持ち上げ位置の真下に配置）
    /// </summary>
    public void Drop()
    {
        if (!_isPickedUp) return;
        
        // 現在の胸元位置を記録（親子関係解除前に）
        Vector3 currentCarryPosition = transform.position;
        
        _isPickedUp = false;
        
        ReleaseParentRelation();
        SetDropPosition(currentCarryPosition);
        EnablePhysics();
        EnableCollision();
    }
    
    /// <summary>
    /// 持ち上げ状態を取得
    /// </summary>
    public bool IsPickedUp()
    {
        return _isPickedUp;
    }
    #endregion

    #region 3. 物理制御システム
    /// <summary>
    /// 物理演算を無効化
    /// </summary>
    private void DisablePhysics()
    {
        if (_rigidbody != null)
        {
            _rigidbody.isKinematic = true;
            _rigidbody.useGravity = false;
        }
    }
    
    /// <summary>
    /// 物理演算を有効化
    /// </summary>
    private void EnablePhysics()
    {
        if (_rigidbody != null)
        {
            _rigidbody.isKinematic = false;
            _rigidbody.useGravity = true;
        }
    }
    
    /// <summary>
    /// コリジョンを無効化
    /// </summary>
    private void DisableCollision()
    {
        if (_collider != null)
        {
            _collider.enabled = false;
        }
    }
    
    /// <summary>
    /// コリジョンを有効化
    /// </summary>
    private void EnableCollision()
    {
        if (_collider != null)
        {
            _collider.enabled = true;
        }
    }
    #endregion

    #region 4. 状態管理システム
    /// <summary>
    /// 親子関係の設定
    /// </summary>
    private void SetupParentRelation(Transform parent)
    {
        transform.SetParent(parent);
    }
    
    /// <summary>
    /// 親子関係の解除
    /// </summary>
    private void ReleaseParentRelation()
    {
        transform.SetParent(null);
    }
    
    /// <summary>
    /// 持ち上げ位置の設定
    /// </summary>
    private void SetCarryPosition()
    {
        transform.localPosition = carryOffset;
        transform.localRotation = Quaternion.identity;
    }
    
    /// <summary>
    /// ドロップ位置の設定（胸元位置の真下に配置）
    /// </summary>
    private void SetDropPosition(Vector3 carryPosition)
    {
        Vector3 dropPosition = new Vector3(
            carryPosition.x,
            FindGroundLevel(carryPosition),
            carryPosition.z
        );
        transform.position = dropPosition;
    }
    
    /// <summary>
    /// 地面レベルの検出
    /// </summary>
    private float FindGroundLevel(Vector3 position)
    {
        // 上から下にレイキャストで地面を探す
        if (Physics.Raycast(position, Vector3.down, out RaycastHit hit, 10f))
        {
            float itemHeight;
            if (_collider != null)
            {
                itemHeight = _collider.bounds.extents.y;
            }
            else
            {
                // 警告を出してデフォルト値使用
                Debug.LogWarning($"[ItemPickup] {gameObject.name}: Collider not found. Using default height 0.5m");
                itemHeight = 0.5f;
            }
            return hit.point.y + itemHeight;
        }
        
        // 地面が見つからない場合は現在の高さを維持
        return position.y;
    }
    
    /// <summary>
    /// コンポーネントの初期化
    /// </summary>
    private void InitializeComponents()
    {
        // Rigidbody取得または追加
        _rigidbody = GetComponent<Rigidbody>();
        if (_rigidbody == null && usePhysics)
        {
            _rigidbody = gameObject.AddComponent<Rigidbody>();
        }
        
        // Collider取得（キャッシュ化）
        _collider = GetComponent<Collider>();
        if (_collider == null)
        {
            Debug.LogWarning($"[ItemPickup] {gameObject.name}: No Collider found. This item may not be pickupable and drop height will be inaccurate.");
        }
    }
    #endregion
}