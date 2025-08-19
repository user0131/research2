// LLMCommunicatorクラス - 統一通信窓口・コマンド配送
// 構成: 1=Core, 2=Public API, 3=Backend通信, 4=コマンド処理, 5=ユーティリティ
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using System.Text;
using System;

[System.Serializable]
public class LogRequest
{
    public List<string> logs;
}

[System.Serializable]
public class CommandResponse
{
    public string command;
    public string reasoning;
    public bool success;
    public string current_task;
    public string progress;
    // 座標移動用の追加フィールド
    public float? x;
    public float? y;
    public float? z;
}

public class LLMCommunicator : MonoBehaviour
{
    [Header("Backend Settings")]
    public string backendUrl = "http://localhost:5000";
    public float requestTimeout = 30f;
    
    [Header("Debug Settings")]
    public bool enableDebugLogs = true;
    
    private CommandExecutor commandExecutor;
    private AccessibilityNarrator logManager;
    private bool isProcessingRequest = false;
    
    public static LLMCommunicator Instance;

    #region 1. Core lifecycle & setup
    void Awake()
    {
        if (Instance == null)
        {
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }
        else
        {
            Destroy(gameObject);
        }
    }
    
    void Start()
    {
        commandExecutor = FindFirstObjectByType<CommandExecutor>();
        if (commandExecutor == null)
        {
            Debug.LogError("[LLMCommunicator] CommandExecutor not found!");
        }
        
        logManager = AccessibilityNarrator.Instance;
        if (logManager == null)
        {
            Debug.LogError("[LLMCommunicator] AccessibilityNarrator not found!");
        }
        
        if (enableDebugLogs)
        {
            Debug.Log("[LLMCommunicator] ログ管理システムを開始しました（コマンド完了時のみ送信）");
        }
    }
    
    void OnDestroy()
    {
        StopAllCoroutines();
    }
    #endregion

    #region 2. Public API
    /// <summary>
    /// コマンド実行完了時に呼び出される（コマンド完了時のみログ送信）
    /// </summary>
    public void OnCommandCompleted()
    {
        if (enableDebugLogs)
        {
            Debug.Log("[LLMCommunicator] コマンド実行完了 - ログ収集開始");
        }
        
        // AccessibilityNarratorにログ収集を依頼
        if (logManager != null && !isProcessingRequest)
        {
            RequestSituationLogs();
        }
    }
    #endregion

    #region 3. Backend通信
    
    private IEnumerator SendLogsToBackend(List<string> logs)
    {
        isProcessingRequest = true;
        
        // リクエストデータの作成
        LogRequest request = new LogRequest();
        request.logs = new List<string>(logs);
        
        string jsonData = JsonUtility.ToJson(request);
        
        // HTTPリクエストの作成
        using (UnityWebRequest webRequest = new UnityWebRequest(backendUrl + "/api/process_logs", "POST"))
        {
            byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonData);
            webRequest.uploadHandler = new UploadHandlerRaw(bodyRaw);
            webRequest.downloadHandler = new DownloadHandlerBuffer();
            webRequest.SetRequestHeader("Content-Type", "application/json");
            webRequest.timeout = (int)requestTimeout;
            
            yield return webRequest.SendWebRequest();
            
            if (webRequest.result == UnityWebRequest.Result.Success)
            {
                string responseText = webRequest.downloadHandler.text;
                
                try
                {
                    CommandResponse response = JsonUtility.FromJson<CommandResponse>(responseText); // TODO: 戻り値について、内容をbackend修正時に再構成する必要あり。
                    
                    if (response.success && !string.IsNullOrEmpty(response.command))
                    {
                        // コマンド実行時にタスク情報も表示(デバッグ用)
                        Debug.Log($"[LLM] {response.command} コマンドを実行 | タスク: {response.current_task}");
                        
                        // コマンド実行開始（CommandExecutorで状態管理）
                        
                        // 座標移動コマンドの場合、座標情報を使用
                        if (response.command == "navigate" && response.x.HasValue && response.y.HasValue && response.z.HasValue)
                        {
                            string navigateCommand = $"navigate:{response.x},{response.y},{response.z}";
                            ExecuteCommand(navigateCommand);
                        }
                        else
                        {
                            // 通常のコマンドを実行
                            ExecuteCommand(response.command);
                        }
                    }
                }
                catch (Exception e)
                {
                    Debug.LogError("[LLMCommunicator] レスポンス解析エラー: " + e.Message);
                }
            }
            else
            {
                Debug.LogError($"[LLMCommunicator] 通信エラー: {webRequest.error}");
            }
        }
        
        isProcessingRequest = false;
    }

    /// <summary>
    /// AccessibilityNarratorにログ収集を依頼し、取得したログをバックエンドに送信
    /// </summary>
    private void RequestSituationLogs()
    {
        // AccessibilityNarratorからログを能動的に収集
        List<string> situationLogs = logManager.CollectCurrentSituationLogs();
        
        if (situationLogs != null && situationLogs.Count > 0)
        {
            if (enableDebugLogs)
            {
                Debug.Log($"[LLMCommunicator] ログ収集完了 - バックエンドに送信（{situationLogs.Count}件）");
            }
            
            // 収集したログをバックエンドに送信
            StartCoroutine(SendLogsToBackend(situationLogs));
        }
        else
        {
            if (enableDebugLogs)
            {
                Debug.LogWarning("[LLMCommunicator] 収集されたログがありません");
            }
        }
    }
    #endregion

    #region 4. コマンド処理(取得したコマンドを、CommandExecutorに渡して実行)
    
    private void ExecuteCommand(string command)
    {
        if (commandExecutor == null)
        {
            Debug.LogError("[LLMCommunicator] CommandExecutor が見つかりません");
            return;
        }
        
        // 正規表現による方向コマンドの変換
        string normalizedCommand = NormalizeCommand(command);
        
        switch (normalizedCommand.ToLower())
        {
            case "north":
                commandExecutor.ExecuteCommand("north");
                break;
            case "south":
                commandExecutor.ExecuteCommand("south");
                break;
            case "east":
                commandExecutor.ExecuteCommand("east");
                break;
            case "west":
                commandExecutor.ExecuteCommand("west");
                break;
            case "pickup":
                commandExecutor.ExecuteCommand("pickup");
                break;
            case "interact":
                commandExecutor.ExecuteCommand("interact");
                break;
            case "e":
            case "E":
                commandExecutor.ExecuteCommand("interact"); // Eコマンドはinteractとしてマップ
                break;
            case "wait":
                commandExecutor.ExecuteCommand("wait");
                break;
            default:
                Debug.LogWarning($"[LLMCommunicator] 不明なコマンド: {command} (正規化後: {normalizedCommand})");
                break;
        }
    }
    
    private string NormalizeCommand(string command)
    {
        // 方向コマンドの正規表現マッピング
        string normalized = command.Trim();
        
        // +Z, +z → north
        if (System.Text.RegularExpressions.Regex.IsMatch(normalized, @"^\+[Zz]$"))
        {
            return "north";
        }
        // -Z, -z → south
        if (System.Text.RegularExpressions.Regex.IsMatch(normalized, @"^-[Zz]$"))
        {
            return "south";
        }
        // +X, +x → east
        if (System.Text.RegularExpressions.Regex.IsMatch(normalized, @"^\+[Xx]$"))
        {
            return "east";
        }
        // -X, -x → west
        if (System.Text.RegularExpressions.Regex.IsMatch(normalized, @"^-[Xx]$"))
        {
            return "west";
        }
        
        return normalized;
    }
    #endregion
}