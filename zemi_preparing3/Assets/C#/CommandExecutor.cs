using UnityEngine;
using StarterAssets;
using System.Collections;

public class CommandExecutor : MonoBehaviour
{
    [Header("Dependencies")]
    public StarterAssetsInputs inputSystem;
    public PlayerPickupController pickupController;
    
    [Header("Movement Settings")]
    public float movementDistance = 0.5f; // 移動コマンドの移動距離（単位）
    public float actionPressDuration = 0.1f; // アクションボタンの押下時間
    
    [Header("Debug")]
    public bool enableDebugLogs = true;
    
    private bool isExecutingCommand = false;
    
    void Start()
    {
        // 依存関係を自動取得
        if (inputSystem == null)
        {
            inputSystem = GetComponent<StarterAssetsInputs>();
        }
        
        if (pickupController == null)
        {
            pickupController = GetComponent<PlayerPickupController>();
        }
        
        if (inputSystem == null || pickupController == null)
        {
            Debug.LogError("[CommandExecutor] Required components not found!");
        }
    }
    
    /// <summary>
    /// コマンドを実行
    /// </summary>
    public void ExecuteCommand(string command, string reasoning = "")
    {
        if (isExecutingCommand)
        {
            if (enableDebugLogs)
            {
                Debug.LogWarning($"[CommandExecutor] Already executing command. Skipping: {command}");
            }
            return;
        }
        
        StartCoroutine(ExecuteCommandCoroutine(command, reasoning));
    }
    
    private IEnumerator ExecuteCommandCoroutine(string command, string reasoning)
    {
        isExecutingCommand = true;
        
        // 簡潔なログのみ出力
        if (enableDebugLogs)
        {
            Debug.Log($"[CommandExecutor] Executing: {command}");
        }
        
        // コマンド実行
        switch (command.ToLower())
        {
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
            case "pickup":
                yield return ExecutePickup();
                break;
            case "interact":
                yield return ExecuteInteract();
                break;
            case "wait":
                yield return ExecuteWait();
                break;
            default:
                if (enableDebugLogs)
                {
                    Debug.LogWarning($"[CommandExecutor] Unknown command: {command}");
                }
                break;
        }
        
        isExecutingCommand = false;
        
        // コマンド実行完了をAccessibilityNarratorに通知
        if (AccessibilityNarrator.Instance != null)
        {
            AccessibilityNarrator.Instance.OnCommandCompleted();
        }
    }
    
    private IEnumerator ExecuteMovement(Vector2 direction)
    {
        if (inputSystem == null)
        {
            if (enableDebugLogs)
            {
                Debug.LogError("[CommandExecutor] InputSystem not found!");
            }
            yield break;
        }
        
        // 移動開始の詳細ログを削除
        // 移動開始位置を記録
        Vector3 startPosition = transform.position;
        
        // 移動時間を調整してゆとりのある移動距離にする######### TODO
        // 実際の移動速度を測定して調整
        float movementTime = 0.5f; // より長い移動距離のための時間（調整値）
        
        // 移動入力を設定
        inputSystem.MoveInput(direction);
        
        // 指定時間だけ移動
        yield return new WaitForSeconds(movementTime);
        
        // 移動を停止
        inputSystem.MoveInput(Vector2.zero);
        
        // 移動完了の詳細ログも削除（必要時のみ有効化）
        // if (enableDebugLogs)
        // {
        //     float actualDistance = Vector3.Distance(startPosition, transform.position);
        //     Debug.Log($"[CommandExecutor] Movement completed. Actual distance: {actualDistance:F2}");
        // }
    }
    
    private IEnumerator ExecutePickup()
    {
        if (inputSystem == null)
        {
            if (enableDebugLogs)
            {
                Debug.LogError("[CommandExecutor] InputSystem not found!");
            }
            yield break;
        }
        
        // ピックアップ詳細ログを削除
        
        // ピックアップ入力を設定
        inputSystem.PickupInput(true);
        
        // 短時間待機
        yield return new WaitForSeconds(actionPressDuration);
        
        // ピックアップ入力を解除
        inputSystem.PickupInput(false);
        
        // 完了ログも削除
    }
    
    private IEnumerator ExecuteInteract()
    {
        if (inputSystem == null)
        {
            if (enableDebugLogs)
            {
                Debug.LogError("[CommandExecutor] InputSystem not found!");
            }
            yield break;
        }
        
        // インタラクト詳細ログを削除
        
        // インタラクト入力を設定
        inputSystem.InteractInput(true);
        
        // 短時間待機
        yield return new WaitForSeconds(actionPressDuration);
        
        // インタラクト入力を解除
        inputSystem.InteractInput(false);
        
        // 完了ログも削除
    }
    
    private IEnumerator ExecuteWait()
    {
        // 少し待機
        yield return new WaitForSeconds(0.5f);
        
        // 待機完了後、強制的に現在の状況を報告
        AccessibilityNarrator narrator = AccessibilityNarrator.Instance;
        if (narrator != null)
        {
            // 現在の状況を再度ナレーション
            narrator.NarrateCurrentSituation();
        }
        
        Debug.Log("[CommandExecutor] 待機完了");
    }
    
    /// <summary>
    /// 現在コマンドを実行中かどうか
    /// </summary>
    public bool IsExecutingCommand()
    {
        return isExecutingCommand;
    }
    
    /// <summary>
    /// 現在実行中のコマンドを停止
    /// </summary>
    public void StopCurrentCommand()
    {
        StopAllCoroutines();
        
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
    
    private void OnDestroy()
    {
        StopAllCoroutines();
    }
} 