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
    public string step_id;        // 実行中のステップID（オプション）
    public string error_info;     // エラー情報（オプション）
}

[System.Serializable]
public class CommandResponse
{
    public string command;
    public string reasoning;
    public bool success;
    public string current_task;
    public string step_id;  // ステップID（完了報告用）
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
    private string currentStepId = null;  // 現在実行中のステップID
    
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
            Debug.Log("[LLMCommunicator] ログ管理システムを開始しました");
        }
        
        // 初期化時に最初のログをバックエンドに送信
        StartCoroutine(SendInitialLogs());
    }
    
    void OnDestroy()
    {
        StopAllCoroutines();
    }
    
    /// <summary>
    /// 初期化時にログを送信する（コマンド完了を待たずに）
    /// </summary>
    private IEnumerator SendInitialLogs()
    {
        // 少し待機してからログを収集（他のコンポーネントの初期化を待つ）
        yield return new WaitForSeconds(1.0f);
        
        if (enableDebugLogs)
        {
            Debug.Log("[LLMCommunicator] 初期ログ送信開始");
        }
        
        // 初期ログを収集してバックエンドに送信
        if (logManager != null && !isProcessingRequest)
        {
            RequestSituationLogs();
        }
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
        
        // ログを1つの文字列に結合（改行で区切る）
        string combinedLog = string.Join("\n", logs);
        
        // リクエストデータの作成（1つの文字列として格納）
        LogRequest request = new LogRequest();
        request.logs = new List<string> { combinedLog };
        request.step_id = currentStepId;  // 現在のステップIDを設定（あれば）
        request.error_info = null;  // エラー情報は今後実装
        
        string jsonData = JsonUtility.ToJson(request);
        
        // HTTPリクエストの作成
        using (UnityWebRequest webRequest = new UnityWebRequest(backendUrl + "/api/process", "POST"))
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
                        // 新しいステップIDを保存
                        if (!string.IsNullOrEmpty(response.step_id))
                        {
                            currentStepId = response.step_id;
                            Debug.Log($"[LLM] ステップID更新: {currentStepId}");
                        }
                        
                        // コマンド実行時にタスク情報も表示(デバッグ用)
                        Debug.Log($"[LLM] {response.command} コマンドを実行 | タスク: {response.current_task} | ステップ: {response.step_id}");
                        
                        // コマンド実行開始（CommandExecutorで状態管理）
                        
                        // 座標移動コマンドの場合、座標情報を使用（Y座標は省略可能）
                        if (response.command == "navigate" && response.x.HasValue && response.z.HasValue)
                        {
                            // Y座標が指定されていない場合は0を使用
                            float yValue = response.y.HasValue ? response.y.Value : 0f;
                            string navigateCommand = $"navigate:{response.x},{yValue},{response.z}";
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
                // バックエンドに送信されるのと同じ内容を表示
                System.Text.StringBuilder logBuilder = new System.Text.StringBuilder();
                logBuilder.AppendLine($"[LLMCommunicator] ログ収集完了 - バックエンドに送信（{situationLogs.Count}件）");
                logBuilder.AppendLine("=== バックエンド送信内容（1つの文字列として送信） ===");
                
                // 実際に送信される形式で表示
                string combinedLog = string.Join("\n", situationLogs);
                logBuilder.AppendLine(combinedLog);
                
                logBuilder.AppendLine("=======================");
                
                // まとめて1回で出力
                Debug.Log(logBuilder.ToString());
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
        
        // コマンドをそのままCommandExecutorに渡す
        // navigateコマンドは "navigate:x,y,z" 形式で既に処理済み
        // その他のコマンドは直接実行
        switch (command.ToLower())
        {
            case "pickup":
                commandExecutor.ExecuteCommand("pickup");
                break;
            case "interact":
                commandExecutor.ExecuteCommand("interact");
                break;
            case "e":
                commandExecutor.ExecuteCommand("interact"); // Eコマンドはinteractとしてマップ
                break;
            case "wait":
                commandExecutor.ExecuteCommand("wait");
                break;
            default:
                // navigateコマンドまたはその他のコマンドをそのまま実行
                commandExecutor.ExecuteCommand(command);
                break;
        }
    }
    #endregion
}