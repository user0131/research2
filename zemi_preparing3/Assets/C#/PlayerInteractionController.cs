// PlayerInteractionController - プレイヤーの操作制御システム
// プレイヤーのアイテム拾い、置き、TVの操作を制御し、イベント通知を一元管理
// 構成: 1=Core, 2=アイテム操作, 3=TV操作, 4=検出システム, 5=イベント通知

using UnityEngine;
using StarterAssets;

public class PlayerInteractionController : MonoBehaviour
{
    [Header("Detection Settings")]
    public float pickupRange = 2.0f;
    public LayerMask pickupLayer = -1;
    
    [Header("Carry Position")]
    public Transform carryPosition;
    
    // コンポーネント参照
    private StarterAssetsInputs input;
    
    // 状態管理（private フィールド）
    private ItemPickup _currentNearbyItem;
    private ItemPickup _carriedItem;
    private TVInteract _currentNearbyTV;
    
    // 読み取り専用プロパティ（外部アクセス用）
    public ItemPickup CurrentNearbyItem => _currentNearbyItem;
    public ItemPickup CarriedItem => _carriedItem;
    public TVInteract CurrentNearbyTV => _currentNearbyTV;

    #region 1. Core Lifecycle
    void Start()
    {
        // コンポーネント取得
        input = GetComponent<StarterAssetsInputs>();
        if (input == null)
        {
            // PlayerArmatureから取得を試行
            input = FindFirstObjectByType<StarterAssetsInputs>();
        }
        
        if (input == null)
        {
            Debug.LogError("[PlayerInteractionController] StarterAssetsInputs not found!");
        }
        
        // キャリーポジション初期化
        InitializeCarryPosition();
    }
    
    void Update()
    {
        // 検出システム更新
        CheckForNearbyItems();
        CheckForNearbyTVs();
        
        // 入力処理
        ProcessUserInput();
    }
    #endregion

    #region 2. アイテム操作システム
    /// <summary>
    /// アイテムの拾い上げ処理
    /// </summary>
    private void TryPickupItem()
    {
        if (_currentNearbyItem != null)
        {
            _currentNearbyItem.PickUp(carryPosition);
            _carriedItem = _currentNearbyItem;
            
            // イベント通知
            NotifyItemPickedUp(_carriedItem.itemName);
            
            _currentNearbyItem = null;
        }
    }
    
    /// <summary>
    /// アイテムのドロップ処理
    /// </summary>
    private void DropItem()
    {
        if (_carriedItem != null)
        {
            string itemName = _carriedItem.itemName;
            
            // Drop実行（内部で適切な位置に配置される）
            _carriedItem.Drop();
            
            // Drop後の実際の位置を取得
            Vector3 dropPosition = _carriedItem.transform.position;
            
            // イベント通知
            NotifyItemDropped(itemName, dropPosition);
            
            _carriedItem = null;
        }
    }
    #endregion

    #region 3. TV操作システム
    /// <summary>
    /// TV操作の実行
    /// </summary>
    private void TryInteractWithTV()
    {
        if (_currentNearbyTV != null)
        {
            string deviceName = _currentNearbyTV.deviceName;
            bool wasOn = _currentNearbyTV.IsOn();
            
            _currentNearbyTV.ToggleTV();
            
            // イベント通知
            NotifyTVToggled(deviceName, !wasOn);
        }
    }
    #endregion

    #region 4. 検出システム
    /// <summary>
    /// 近くのアイテム検出
    /// </summary>
    private void CheckForNearbyItems()
    {
        // 近くのItemPickupオブジェクトを検索
        Collider[] colliders = Physics.OverlapSphere(transform.position, pickupRange, pickupLayer);
        
        ItemPickup nearestItem = null;
        float nearestDistance = float.MaxValue;
        
        foreach (Collider col in colliders)
        {
            ItemPickup item = col.GetComponent<ItemPickup>();
            if (item != null && !item.IsPickedUp())
            {
                float distance = Vector3.Distance(transform.position, col.transform.position);
                if (distance < nearestDistance)
                {
                    nearestDistance = distance;
                    nearestItem = item;
                }
            }
        }
        
        // 状態が変化した場合のみ処理
        if (_currentNearbyItem != nearestItem)
        {
            _currentNearbyItem = nearestItem;
            
            if (_currentNearbyItem != null)
            {
                NotifyNearbyItemDetected(_currentNearbyItem.itemName, nearestDistance);
            }
            else
            {
                NotifyNearbyItemReset();
            }
        }
    }
    
    /// <summary>
    /// 近くのTV検出
    /// </summary>
    private void CheckForNearbyTVs()
    {
        // 近くのTVInteractオブジェクトを検索
        Collider[] colliders = Physics.OverlapSphere(transform.position, pickupRange, pickupLayer);
        
        TVInteract nearestTV = null;
        float nearestDistance = float.MaxValue;
        
        foreach (Collider col in colliders)
        {
            TVInteract tv = col.GetComponent<TVInteract>();
            if (tv != null)
            {
                // TVのボタンの位置との距離を計算
                float distance = Vector3.Distance(transform.position, tv.GetButtonPosition());
                if (distance < nearestDistance && distance <= tv.interactRange)
                {
                    nearestDistance = distance;
                    nearestTV = tv;
                }
            }
        }
        
        // 状態が変化した場合のみ処理
        if (_currentNearbyTV != nearestTV)
        {
            _currentNearbyTV = nearestTV;
            
            if (_currentNearbyTV != null)
            {
                NotifyNearbyTVDetected(_currentNearbyTV.deviceName, nearestDistance, _currentNearbyTV.IsOn());
            }
            else
            {
                NotifyNearbyTVReset();
            }
        }
    }
    #endregion

    #region 5. イベント通知システム
    /// <summary>
    /// アイテム拾い上げイベント通知
    /// </summary>
    private void NotifyItemPickedUp(string itemName)
    {
        if (AccessibilityNarrator.Instance != null)
        {
            AccessibilityNarrator.Instance.OnItemPickedUp(itemName);
        }
    }
    
    /// <summary>
    /// アイテムドロップイベント通知
    /// </summary>
    private void NotifyItemDropped(string itemName, Vector3 dropPosition)
    {
        if (AccessibilityNarrator.Instance != null)
        {
            AccessibilityNarrator.Instance.OnItemDropped(itemName, dropPosition);
        }
    }
    
    /// <summary>
    /// TV操作イベント通知
    /// </summary>
    private void NotifyTVToggled(string deviceName, bool isOn)
    {
        if (AccessibilityNarrator.Instance != null)
        {
            AccessibilityNarrator.Instance.OnTVToggled(deviceName, isOn);
        }
    }
    
    /// <summary>
    /// 近くのアイテム検出イベント通知
    /// </summary>
    private void NotifyNearbyItemDetected(string itemName, float distance)
    {
        if (AccessibilityNarrator.Instance != null)
        {
            AccessibilityNarrator.Instance.OnNearbyItemDetected(itemName, distance);
        }
    }
    
    /// <summary>
    /// 近くのアイテムリセットイベント通知
    /// </summary>
    private void NotifyNearbyItemReset()
    {
        if (AccessibilityNarrator.Instance != null)
        {
            AccessibilityNarrator.Instance.ResetNearbyItem();
        }
    }
    
    /// <summary>
    /// 近くのTV検出イベント通知
    /// </summary>
    private void NotifyNearbyTVDetected(string deviceName, float distance, bool isOn)
    {
        if (AccessibilityNarrator.Instance != null)
        {
            AccessibilityNarrator.Instance.OnNearbyTVDetected(deviceName, distance, isOn);
        }
    }
    
    /// <summary>
    /// 近くのTVリセットイベント通知
    /// </summary>
    private void NotifyNearbyTVReset()
    {
        if (AccessibilityNarrator.Instance != null)
        {
            AccessibilityNarrator.Instance.ResetNearbyTV();
        }
    }
    #endregion

    #region 6. ヘルパーメソッド
    /// <summary>
    /// キャリーポジションの初期化
    /// </summary>
    private void InitializeCarryPosition()
    {
        if (carryPosition == null)
        {
            GameObject carryPoint = new GameObject("CarryPoint");
            carryPoint.transform.SetParent(transform);
            carryPoint.transform.localPosition = new Vector3(0, 1.5f, 1f);
            carryPosition = carryPoint.transform;
        }
    }
    
    /// <summary>
    /// ユーザー入力の処理
    /// </summary>
    private void ProcessUserInput()
    {
        // Pickup入力をチェック
        if (input.pickup)
        {
            if (_carriedItem == null)
            {
                // アイテムを持っていない場合は拾う
                TryPickupItem();
            }
            else
            {
                // アイテムを持っている場合は置く
                DropItem();
            }
            
            // 入力をリセット
            input.pickup = false;
        }
        
        // Interact入力をチェック
        if (input.interact)
        {
            TryInteractWithTV();
            
            // 入力をリセット
            input.interact = false;
        }
    }
    #endregion

    #region 7. Debug & Visualization
    /// <summary>
    /// デバッグ用：検出範囲を可視化
    /// </summary>
    void OnDrawGizmosSelected()
    {
        // エディタでpickupRangeを表示
        Gizmos.color = Color.yellow;
        Gizmos.DrawWireSphere(transform.position, pickupRange);
    }
    #endregion
}