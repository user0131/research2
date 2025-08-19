using UnityEngine;

public class TVInteract : MonoBehaviour
{
    [Header("TV Settings")]
    public string deviceName = "TV";
    public float interactRange = 4.0f;
    
    [Header("Screen Settings")]
    public GameObject screenObject; // TVのScreenオブジェクト
    public Material onMaterial; // 光った時のマテリアル
    public Material offMaterial; // 消えた時のマテリアル
    
    [Header("Button Settings")]
    public Transform buttonTransform; // TVのボタンの位置
    
    private bool isOn = false;
    private Renderer screenRenderer;
    
    void Start()
    {
        // Screenオブジェクトのレンダラーを取得
        if (screenObject != null)
        {
            screenRenderer = screenObject.GetComponent<Renderer>();
        }
        else
        {
            // screenObjectが設定されていない場合、子オブジェクトから探す
            screenRenderer = GetComponentInChildren<Renderer>();
        }
        
        // 初期状態を設定
        SetScreenState(false);
    }
    
    public void ToggleTV()
    {
        isOn = !isOn;
        SetScreenState(isOn);
        
        // Narratorにイベントを通知
        if (AccessibilityNarrator.Instance != null)
        {
            AccessibilityNarrator.Instance.OnTVToggled(deviceName, isOn);
        }
    }
    
    private void SetScreenState(bool turnOn)
    {
        if (screenRenderer == null) return;
        
        if (turnOn)
        {
            // TVを点ける
            if (onMaterial != null)
            {
                screenRenderer.material = onMaterial;
            }
            else
            {
                // マテリアルが設定されていない場合、色を変更
                screenRenderer.material.color = Color.white;
                screenRenderer.material.SetColor("_EmissionColor", Color.white);
            }
        }
        else
        {
            // TVを消す
            if (offMaterial != null)
            {
                screenRenderer.material = offMaterial;
            }
            else
            {
                // マテリアルが設定されていない場合、色を変更
                screenRenderer.material.color = Color.black;
                screenRenderer.material.SetColor("_EmissionColor", Color.black);
            }
        }
    }
    
    public bool IsOn()
    {
        return isOn;
    }
    
    public Vector3 GetButtonPosition()
    {
        if (buttonTransform != null)
        {
            return buttonTransform.position;
        }
        else
        {
            // ボタンの位置が設定されていない場合、オブジェクトの位置を返す
            return transform.position;
        }
    }
} 