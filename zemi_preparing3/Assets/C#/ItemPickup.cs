using UnityEngine;

public class ItemPickup : MonoBehaviour
{
    [Header("Item Settings")]
    public string itemName = "PC";
    public float pickupRange = 2.0f;
    
    [Header("Physics")]
    public bool usePhysics = true;
    
    private Rigidbody rb;
    private bool isPickedUp = false;
    
    void Start()
    {
        rb = GetComponent<Rigidbody>();
        
        // もしRigidbodyが存在しない場合は追加
        if (rb == null && usePhysics)
        {
            rb = gameObject.AddComponent<Rigidbody>();
        }
    }
    
    public void PickUp(Transform parent)
    {
        if (isPickedUp) return;
        
        isPickedUp = true;
        
        // プレイヤーの子オブジェクトにする
        transform.SetParent(parent);
        
        // 物理演算を無効にする
        if (rb != null)
        {
            rb.isKinematic = true;
            rb.useGravity = false;
        }
        
        // コライダーを無効にする
        Collider col = GetComponent<Collider>();
        if (col != null)
        {
            col.enabled = false;
        }
        
        // プレイヤーの胸元近くに配置
        transform.localPosition = new Vector3(0, 0.1f, 0.1f);
        transform.localRotation = Quaternion.identity;
        
        // Narratorにイベントを通知
        if (AccessibilityNarrator.Instance != null)
        {
            AccessibilityNarrator.Instance.OnItemPickedUp(itemName);
        }
    }
    
    public void Drop()
    {
        if (!isPickedUp) return;
        
        isPickedUp = false;
        
        // 親から切り離す
        transform.SetParent(null);
        
        // 物理演算を有効にする
        if (rb != null)
        {
            rb.isKinematic = false;
            rb.useGravity = true;
        }
        
        // コライダーを有効にする
        Collider col = GetComponent<Collider>();
        if (col != null)
        {
            col.enabled = true;
        }
        
        // Narratorにイベントを通知
        if (AccessibilityNarrator.Instance != null)
        {
            AccessibilityNarrator.Instance.OnItemDropped(itemName, transform.position);
        }
    }
    
    public bool IsPickedUp()
    {
        return isPickedUp;
    }
} 