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
}

public class LLMCommunicator : MonoBehaviour
{
    [Header("Backend Settings")]
    public string backendUrl = "http://localhost:5000";
    public float requestTimeout = 30f;
    
    [Header("Debug Settings")]
    public bool enableDebugLogs = true;
    
    private CommandExecutor commandExecutor;
    private bool isProcessingRequest = false;
    private bool isExecutingCommand = false;
    private List<string> latestSituationLogs = new List<string>();
    private bool hasPendingSituation = false;
    
    public static LLMCommunicator Instance;
    
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
        
        // アプリケーションログを監視
        Application.logMessageReceived += OnLogReceived;
        
        // 起動ログを削除（簡潔に）
    }
    
    void OnDestroy()
    {
        Application.logMessageReceived -= OnLogReceived;
    }
    
    private void OnLogReceived(string logString, string stackTrace, LogType type)
    {
        // [Narrator] === 現在の状況 === を検出
        if (logString.Contains("[Narrator] === 現在の状況 ==="))
        {
            // 新しい状況ログの開始を検出
            latestSituationLogs.Clear();
            latestSituationLogs.Add(logString);
            hasPendingSituation = true;
            return;
        }
        
        // 状況ログを蓄積中の場合、ログを追加
        if (hasPendingSituation && logString.StartsWith("["))
        {
            latestSituationLogs.Add(logString);
            
            // [可能なコマンド] が来たら状況ログ完了として判定
            if (logString.Contains("[可能なコマンド]"))
            {
                // コマンド実行中でなければ即座に送信
                if (!isExecutingCommand)
                {
                    ProcessLatestSituation();
                }
            }
        }
        
        // コマンド実行完了を検出
        if (logString.Contains("コマンド実行完了") || 
            logString.Contains("移動完了") || 
            logString.Contains("アクション完了") ||
            logString.Contains("[Narrator] コマンド実行完了") ||
            logString.Contains("を持ち上げました！") ||
            logString.Contains("を置きました！") ||
            logString.Contains("にしました！"))
        {
            isExecutingCommand = false;
            
            // コマンド実行完了後に最新の状況ログを送信
            if (hasPendingSituation && latestSituationLogs.Count > 0)
            {
                ProcessLatestSituation();
            }
        }
    }
    
    private void ProcessLatestSituation()
    {
        if (isProcessingRequest || isExecutingCommand)
        {
            // 処理中またはコマンド実行中の場合は送信しない
            return;
        }
        
        if (latestSituationLogs.Count == 0)
        {
            return;
        }
        
        // 重要な情報のみログ出力
        if (enableDebugLogs)
        {
            Debug.Log($"[LLMCommunicator] 最新状況を送信中（{latestSituationLogs.Count}件のログ）");
        }
        
        // 最新状況をコピーして送信
        List<string> logsToSend = new List<string>(latestSituationLogs);
        hasPendingSituation = false;
        
        StartCoroutine(SendLogsToBackend(logsToSend));
    }
    
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
                    CommandResponse response = JsonUtility.FromJson<CommandResponse>(responseText);
                    
                    if (response.success && !string.IsNullOrEmpty(response.command))
                    {
                        // コマンド実行時にタスク情報も表示
                        Debug.Log($"[LLM] {response.command} コマンドを実行 | タスク: {response.current_task} | 進捗: {response.progress}");
                        
                        // コマンド実行開始
                        isExecutingCommand = true;
                        
                        // コマンドを実行
                        ExecuteCommand(response.command);
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
    
    private void ExecuteCommand(string command)
    {
        if (commandExecutor == null)
        {
            Debug.LogError("[LLMCommunicator] CommandExecutor が見つかりません");
            isExecutingCommand = false;
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
                isExecutingCommand = false; // waitコマンドは即座に完了
                break;
            default:
                Debug.LogWarning($"[LLMCommunicator] 不明なコマンド: {command} (正規化後: {normalizedCommand})");
                isExecutingCommand = false;
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
    
    // 手動でログを送信するメソッド（テスト用）
    public void SendManualLog(string logMessage)
    {
        List<string> testLogs = new List<string> { logMessage };
        StartCoroutine(SendLogsToBackend(testLogs));
    }
    
    // コマンド実行完了を外部から通知するメソッド
    public void OnCommandCompleted()
    {
        isExecutingCommand = false;
        
        // コマンド実行完了後に最新の状況ログを送信
        if (hasPendingSituation && latestSituationLogs.Count > 0)
        {
            ProcessLatestSituation();
        }
    }
} 