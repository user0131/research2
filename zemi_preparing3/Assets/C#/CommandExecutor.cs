// CommandExecutor - AI専用コマンド実行エンジン
// AIプレイヤーの「仮想的な手」として、人間の入力をシミュレート
// 構成: 1=Core, 2=Public API, 3=メイン実行, 4=人間入力シミュレート, 5=AI専用機能

using UnityEngine;
using StarterAssets;
using System.Collections;

public class CommandExecutor : MonoBehaviour
{
    [Header("Dependencies")]
    public StarterAssetsInputs inputSystem; // 人間と同じ入力システム
    public PlayerPickupController pickupController; // アイテム操作（参照のみ）
    public NavMeshAgentController navMeshController; // AI専用の座標移動
    
    [Header("Movement Settings")]
    public float movementDistance = 0.5f; // 移動コマンドの移動距離（単位）
    public float actionPressDuration = 0.1f; // アクションボタンの押下時間
    
    [Header("Debug")]
    public bool enableDebugLogs = true;
    
    private bool isExecutingCommand = false;

    #region 1. Core lifecycle
    void Start()
    {
        // 依存関係を自動取得
        if (inputSystem == null)
            inputSystem = GetComponent<StarterAssetsInputs>();
        
        if (pickupController == null)
            pickupController = GetComponent<PlayerPickupController>();
        
        if (navMeshController == null)
            navMeshController = GetComponent<NavMeshAgentController>();
        
        // 必須コンポーネントのチェック
        if (inputSystem == null || pickupController == null)
        {
            Debug.LogError("[CommandExecutor] Required components not found!");
        }
    }

    void OnDestroy()
    {
        StopAllCoroutines();
    }
    #endregion

    #region 2. Public API(LLMCommunicatorからコマンドを受け取って実行)
    /// <summary>
    /// LLMCommunicatorからコマンドを受け取って実行
    /// </summary>
    public void ExecuteCommand(string command)
    {
        if (isExecutingCommand)
        {
            if (enableDebugLogs)
            {
                Debug.LogWarning($"[CommandExecutor] Already executing command. Skipping: {command}");
            }
            return;
        }
        
        StartCoroutine(ExecuteCommandCoroutine(command));
    }

    /// <summary>
    /// 現在コマンドを実行中かどうか
    /// </summary>
    public bool IsExecutingCommand()
    {
        return isExecutingCommand;
    }

    /// <summary>
    /// 現在実行中のコマンドを緊急停止
    /// </summary>
    public void StopCurrentCommand()
    {
        StopAllCoroutines();
        
        // 全ての入力をリセット
        if (inputSystem != null)
        {
            inputSystem.MoveInput(Vector2.zero);
            inputSystem.PickupInput(false);
            inputSystem.InteractInput(false);
        }
        
        isExecutingCommand = false;
        
        if (enableDebugLogs)
        {
            Debug.Log("[CommandExecutor] All commands stopped");
        }
    }
    #endregion

    #region 3. メインコマンド実行エンジン(抽象的なコマンドを具体化し、適切なファイル(メソッド)に渡す)
    private IEnumerator ExecuteCommandCoroutine(string command)
    {
        isExecutingCommand = true;
        
        if (enableDebugLogs)
        {
            Debug.Log($"[CommandExecutor] Executing: {command}");
        }
        
        // コマンド振り分け
        switch (command.ToLower())
        {
            // 移動系（人間と同じ）
            case "north":
                yield return ExecuteMovement(Vector2.up);
                break;
            case "south":
                yield return ExecuteMovement(Vector2.down);
                break;
            case "east":
                yield return ExecuteMovement(Vector2.right);
                break;
            case "west":
                yield return ExecuteMovement(Vector2.left);
                break;
            
            // アクション系（人間と同じ）
            case "pickup":
                yield return ExecutePickup();
                break;
            case "interact":
                yield return ExecuteInteract();
                break;
            
            // 特殊系
            case "wait":
                yield return ExecuteWait();
                break;
            
            // AI専用
            default:
                if (command.StartsWith("navigate:"))
                {
                    yield return ExecuteNavigateToPosition(command.Substring(9));
                }
                else if (enableDebugLogs)
                {
                    Debug.LogWarning($"[CommandExecutor] Unknown command: {command}");
                }
                break;
        }
        
        isExecutingCommand = false;
        
        // コマンド完了通知→ログ収集トリガー
        if (AccessibilityNarrator.Instance != null)
        {
            AccessibilityNarrator.Instance.OnCommandCompleted();
        }
    }
    #endregion

    #region 4. 人間入力シミュレート（StarterAssetsInputs経由）
    /// <summary>
    /// 移動コマンド実行（WASDキーのシミュレート）
    /// </summary>
    private IEnumerator ExecuteMovement(Vector2 direction)
    {
        if (inputSystem == null)
        {
            if (enableDebugLogs)
                Debug.LogError("[CommandExecutor] InputSystem not found!");
            yield break;
        }
        
        float movementTime = 0.5f; // 移動時間（TODO: 調整可能にする）
        
        inputSystem.MoveInput(direction);              // キー押下開始
        yield return new WaitForSeconds(movementTime); // 押し続ける
        inputSystem.MoveInput(Vector2.zero);           // キー解放
    }

    /// <summary>
    /// ピックアップ実行（Fキーのシミュレート）
    /// </summary>
    private IEnumerator ExecutePickup()
    {
        if (inputSystem == null)
        {
            if (enableDebugLogs)
                Debug.LogError("[CommandExecutor] InputSystem not found!");
            yield break;
        }
        
        inputSystem.PickupInput(true);                     // Fキー押下
        yield return new WaitForSeconds(actionPressDuration);
        inputSystem.PickupInput(false);                    // Fキー解放
    }

    /// <summary>
    /// インタラクト実行（Eキーのシミュレート）
    /// </summary>
    private IEnumerator ExecuteInteract()
    {
        if (inputSystem == null)
        {
            if (enableDebugLogs)
                Debug.LogError("[CommandExecutor] InputSystem not found!");
            yield break;
        }
        
        inputSystem.InteractInput(true);                   // Eキー押下
        yield return new WaitForSeconds(actionPressDuration);
        inputSystem.InteractInput(false);                  // Eキー解放
    }

    /// <summary>
    /// 待機コマンド
    /// </summary>
    private IEnumerator ExecuteWait()
    {
        yield return new WaitForSeconds(0.5f);
        
        if (enableDebugLogs)
        {
            Debug.Log("[CommandExecutor] 待機完了");
        }
    }
    #endregion

    #region 5. AI専用機能（NavMeshAgent）
    /// <summary>
    /// 座標指定移動（NavMeshAgent使用）
    /// </summary>
    private IEnumerator ExecuteNavigateToPosition(string positionString)
    {
        if (navMeshController == null)
        {
            if (enableDebugLogs)
                Debug.LogError("[CommandExecutor] NavMeshAgentController not found!");
            yield break;
        }
        
        // 座標文字列をパース (例: "10,0,5")
        string[] coords = positionString.Split(',');
        if (coords.Length != 3)
        {
            if (enableDebugLogs)
                Debug.LogError($"[CommandExecutor] Invalid position format: {positionString}");
            yield break;
        }
        
        if (float.TryParse(coords[0], out float x) &&
            float.TryParse(coords[1], out float y) &&
            float.TryParse(coords[2], out float z))
        {
            if (enableDebugLogs)
            {
                Debug.Log($"[CommandExecutor] Navigating to position: ({x}, {y}, {z})");
            }
            
            // AI専用：座標への自動移動
            navMeshController.NavigateToPosition(x, y, z);
            
            // ナビゲーション完了まで待機
            while (navMeshController.IsNavigating())
            {
                yield return new WaitForSeconds(0.1f);
            }
            
            if (enableDebugLogs)
            {
                Debug.Log("[CommandExecutor] Navigation completed");
            }
        }
        else
        {
            if (enableDebugLogs)
            {
                Debug.LogError($"[CommandExecutor] Failed to parse position: {positionString}");
            }
        }
    }
    #endregion
}