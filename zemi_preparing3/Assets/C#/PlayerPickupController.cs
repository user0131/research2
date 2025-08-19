// プレイヤーのアイテム拾い、置き、TVの操作を制御
using UnityEngine;
using StarterAssets;

public class PlayerPickupController : MonoBehaviour
{
    [Header("Pickup Settings")]
    public float pickupRange = 2.0f;
    public LayerMask pickupLayer = -1;
    
    [Header("Carry Position")]
    public Transform carryPosition;
    
    private StarterAssetsInputs input;
    public ItemPickup currentNearbyItem;
    public ItemPickup carriedItem;
    public TVInteract currentNearbyTV;
    
    void Start()
    {
        input = GetComponent<StarterAssetsInputs>();
        
        // キャリーポジションが設定されていない場合、自動で作成
        if (carryPosition == null)
        {
            GameObject carryPoint = new GameObject("CarryPoint");
            carryPoint.transform.SetParent(transform);
            carryPoint.transform.localPosition = new Vector3(0, 1.5f, 1f);
            carryPosition = carryPoint.transform;
        }
    }
    
    void Update()
    {
        // コマンド実行中は検出処理を停止
        if (AccessibilityNarrator.Instance != null && AccessibilityNarrator.Instance.IsCommandExecuting())
        {
            return;
        }
        
        // 近くのアイテムを検出
        CheckForNearbyItems();
        
        // 近くのTVを検出
        CheckForNearbyTVs();
        
        // Pickup入力をチェック
        if (input.pickup)
        {
            if (carriedItem == null)
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
    
    void CheckForNearbyItems()
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
        
        // 現在の近くのアイテムを更新
        if (currentNearbyItem != nearestItem)
        {
            currentNearbyItem = nearestItem;
            
            if (currentNearbyItem != null)
            {
                // Narratorにイベントを通知
                if (AccessibilityNarrator.Instance != null)
                {
                    AccessibilityNarrator.Instance.OnNearbyItemDetected(currentNearbyItem.itemName, nearestDistance);
                }
            }
            else
            {
                // 近くのアイテムがなくなった時の処理
                if (AccessibilityNarrator.Instance != null)
                {
                    AccessibilityNarrator.Instance.ResetNearbyItem();
                }
            }
        }
    }
    
    void TryPickupItem()
    {
        if (currentNearbyItem != null)
        {
            currentNearbyItem.PickUp(carryPosition);
            carriedItem = currentNearbyItem;
            currentNearbyItem = null;
        }
    }
    
    void DropItem()
    {
        if (carriedItem != null)
        {
            carriedItem.Drop();
            carriedItem = null;
        }
    }
    
    void CheckForNearbyTVs()
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
        
        // 現在の近くのTVを更新
        if (currentNearbyTV != nearestTV)
        {
            currentNearbyTV = nearestTV;
            
            if (currentNearbyTV != null)
            {
                // Narratorにイベントを通知
                if (AccessibilityNarrator.Instance != null)
                {
                    AccessibilityNarrator.Instance.OnNearbyTVDetected(currentNearbyTV.deviceName, nearestDistance, currentNearbyTV.IsOn());
                }
            }
            else
            {
                // 近くのTVがなくなった時の処理
                if (AccessibilityNarrator.Instance != null)
                {
                    AccessibilityNarrator.Instance.ResetNearbyTV();
                }
            }
        }
    }
    
    void TryInteractWithTV()
    {
        if (currentNearbyTV != null)
        {
            currentNearbyTV.ToggleTV();
        }
    }
    
    void OnDrawGizmosSelected()
    {
        // エディタでpickupRangeを表示
        Gizmos.color = Color.yellow;
        Gizmos.DrawWireSphere(transform.position, pickupRange);
    }
} 