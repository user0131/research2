// TVInteract - TV操作制御コンポーネント
// TVオブジェクトにアタッチしてON/OFF切り替え機能を提供
// MaterialPropertyBlockでメモリリーク防止、buttonTransformで精密距離計算
// 構成: 1=Core, 2=Public API, 3=表示制御, 4=ユーティリティ

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
    public Transform buttonTransform; // TVのボタンの位置（精密な距離計算用）
    
    // 状態管理
    private bool _isOn = false;
    
    // コンポーネント参照
    private Renderer _screenRenderer;
    
    // MaterialPropertyBlock（メモリリーク防止）
    private MaterialPropertyBlock _propertyBlock;
    private static readonly int ColorID = Shader.PropertyToID("_Color");
    private static readonly int EmissionColorID = Shader.PropertyToID("_EmissionColor");
    
    #region 1. Core Lifecycle
    void Start()
    {
        InitializeComponents();
        InitializePropertyBlock();
        SetInitialState();
    }
    #endregion
    
    #region 2. Public API
    /// <summary>
    /// TV状態の切り替え（PlayerInteractionControllerから呼ばれる）
    /// </summary>
    public void ToggleTV()
    {
        _isOn = !_isOn;
        SetScreenState(_isOn);
    }
    
    /// <summary>
    /// 現在のTV状態を取得
    /// </summary>
    public bool IsOn()
    {
        return _isOn;
    }
    
    /// <summary>
    /// ボタンの位置を取得（距離計算用）
    /// </summary>
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
    #endregion

    #region 3. 表示制御システム
    /// <summary>
    /// スクリーンの表示状態を設定
    /// </summary>
    private void SetScreenState(bool turnOn)
    {
        if (_screenRenderer == null) return;
        
        if (turnOn)
        {
            SetScreenOn();
        }
        else
        {
            SetScreenOff();
        }
    }
    
    /// <summary>
    /// スクリーンをON状態に設定
    /// </summary>
    private void SetScreenOn()
    {
        if (onMaterial != null)
        {
            // 専用マテリアルが設定されている場合はそれを使用
            _screenRenderer.material = onMaterial;
        }
        else
        {
            // マテリアルが未設定の場合、MaterialPropertyBlockで色変更（メモリリークなし）
            _propertyBlock.SetColor(ColorID, Color.white);
            _propertyBlock.SetColor(EmissionColorID, Color.white);
            _screenRenderer.SetPropertyBlock(_propertyBlock);
        }
    }
    
    /// <summary>
    /// スクリーンをOFF状態に設定
    /// </summary>
    private void SetScreenOff()
    {
        if (offMaterial != null)
        {
            // 専用マテリアルが設定されている場合はそれを使用
            _screenRenderer.material = offMaterial;
        }
        else
        {
            // マテリアルが未設定の場合、MaterialPropertyBlockで色変更（メモリリークなし）
            _propertyBlock.SetColor(ColorID, Color.black);
            _propertyBlock.SetColor(EmissionColorID, Color.black);
            _screenRenderer.SetPropertyBlock(_propertyBlock);
        }
    }
    #endregion

    #region 4. ユーティリティメソッド
    /// <summary>
    /// コンポーネントの初期化
    /// </summary>
    private void InitializeComponents()
    {
        // Screenオブジェクトのレンダラーを取得
        if (screenObject != null)
        {
            _screenRenderer = screenObject.GetComponent<Renderer>();
        }
        else
        {
            // screenObjectが設定されていない場合、子オブジェクトから探す
            _screenRenderer = GetComponentInChildren<Renderer>();
        }
    }
    
    /// <summary>
    /// MaterialPropertyBlockの初期化
    /// </summary>
    private void InitializePropertyBlock()
    {
        _propertyBlock = new MaterialPropertyBlock();
    }
    
    /// <summary>
    /// 初期状態の設定
    /// </summary>
    private void SetInitialState()
    {
        SetScreenState(false);
    }
    #endregion
} 