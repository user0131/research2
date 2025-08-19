/*
 * このファイルは新しいLLMCommunicatorシステムでは不要になりました。
 * 
 * 新しいシステムでは、LLMCommunicator.csが自動的に以下の機能を提供します：
 * - ログの自動監視
 * - バックエンドへの自動送信
 * - コマンドの自動実行
 * 
 * このファイルを削除するか、デバッグ機能のみを保持することを推奨します。
 */

using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.IO;
using System.Linq;

public class LLMGameController : MonoBehaviour
{
    [Header("Dependencies")]
    public AccessibilityNarrator accessibilityNarrator;
    public LLMCommunicator llmCommunicator;
    public CommandExecutor commandExecutor;
    
    [Header("Settings")]
    public bool enableLLMControl = true;
    public float logCheckInterval = 3.0f; // ログをチェックする間隔（秒）
    public int maxLogHistory = 50; // 保持するログの最大数
    public float commandExecutionTimeout = 10.0f; // コマンド実行のタイムアウト（秒）
    public float postCommandWaitTime = 2.0f; // コマンド実行後の待機時間（秒）
    
    [Header("Debug")]
    public bool enableDebugLogs = true;
    public bool saveLogsToFile = false;
    public string logFilePath = "llm_game_logs.txt";
    
    [Header("Status")]
    public bool isRunning = false;
    public int totalCommandsExecuted = 0;
    public string lastExecutedCommand = "";
    public bool waitingForCommandResult = false;
    
    private List<string> gameLogHistory = new List<string>();
    private List<string> logsSinceLastSituation = new List<string>();
    private List<string> logsForNextCycle = new List<string>();
    private bool isProcessingCommand = false;
    private string lastSituationMarker = "[Narrator] === 現在の状況 ===";
    private float commandExecutionStartTime = 0f;
    
    void Start()
    {
        // 依存関係を自動取得（手動設定を優先）
        if (accessibilityNarrator == null)
        {
            accessibilityNarrator = FindFirstObjectByType<AccessibilityNarrator>();
        }
        
        if (llmCommunicator == null)
        {
            llmCommunicator = GetComponent<LLMCommunicator>();
        }
        
        if (commandExecutor == null)
        {
            commandExecutor = GetComponent<CommandExecutor>();
        }
        
        // 依存関係チェック
        if (accessibilityNarrator == null || llmCommunicator == null || commandExecutor == null)
        {
            Debug.LogError("[LLMGameController] Required components not found!");
            if (accessibilityNarrator == null) Debug.LogError("AccessibilityNarrator is missing!");
            if (llmCommunicator == null) Debug.LogError("LLMCommunicator is missing!");
            if (commandExecutor == null) Debug.LogError("CommandExecutor is missing!");
            return;
        }
        
        // イベントリスナーを設定
        SetupEventListeners();
        
        // ログキャプチャを開始
        StartLogCapture();
        
        if (enableLLMControl)
        {
            StartLLMControl();
        }
        
        if (enableDebugLogs)
        {
            Debug.Log("[LLMGameController] Initialized successfully");
        }
    }
    
    void SetupEventListeners()
    {
        // 新しいLLMCommunicatorは自動的にログを監視し、コマンドを実行します
        // 詳細ログを削除
    }
    
    void StartLogCapture()
    {
        // Unityのログシステムをキャプチャ（デバッグ用）
        Application.logMessageReceived += OnLogMessageReceived;
    }
    
    void OnLogMessageReceived(string logString, string stackTrace, LogType type)
    {
        // AccessibilityNarratorからのログのみを処理
        if (logString.Contains("[Narrator]"))
        {
            // ログ履歴に追加
            gameLogHistory.Add(logString);
            
            // 最大履歴数を超えた場合、古いログを削除
            if (gameLogHistory.Count > maxLogHistory)
            {
                gameLogHistory.RemoveAt(0);
            }
            
            // コマンド実行後の結果待機中の場合
            if (waitingForCommandResult)
            {
                logsForNextCycle.Add(logString);
                
                // 状況報告を受け取った場合、結果をLLMに送信
                if (logString.Contains(lastSituationMarker))
                {
                    StartCoroutine(ProcessCommandResultLogs());
                }
            }
            else
            {
                // 通常のログ処理
                // 状況報告の区切りをチェック
                if (logString.Contains(lastSituationMarker))
                {
                    // 前回の状況報告以降のログを処理
                    if (logsSinceLastSituation.Count > 0 && enableLLMControl && !isProcessingCommand)
                    {
                        ProcessLogsWithLLM();
                    }
                    
                    // 新しい状況報告を開始
                    logsSinceLastSituation.Clear();
                    logsSinceLastSituation.Add(logString);
                }
                else
                {
                    logsSinceLastSituation.Add(logString);
                }
            }
            
            // ファイルに保存
            if (saveLogsToFile)
            {
                SaveLogToFile(logString);
            }
        }
    }
    
    void ProcessLogsWithLLM()
    {
        // 新しいLLMCommunicatorシステムは自動的にログを監視し、
        // [Narrator] === 現在の状況 === を検出すると自動的にバックエンドに送信します
        // 手動でのログ処理は不要になりました
        
        // 冗長なログを削除
        
        // 統計情報の更新のみ実行
        // 実際のログ処理は LLMCommunicator が自動的に行います
        isProcessingCommand = false;
    }
    
    // 古いイベントハンドラーメソッド（新しいシステムでは不要）
    // 統計情報の更新は新しいシステムで別途実装する必要があります
    
    /*
    void OnCommandReceived(string command, string reasoning)
    {
        if (enableDebugLogs)
        {
            Debug.Log($"[LLMGameController] Command received: {command} - {reasoning}");
        }
        
        // コマンドを実行
        commandExecutor.ExecuteCommand(command, reasoning);
        
        // 統計を更新
        totalCommandsExecuted++;
        lastExecutedCommand = command;
        
        // コマンド実行後の結果待機を開始
        StartCoroutine(WaitForCommandResult());
        
        // 処理完了
        isProcessingCommand = false;
    }
    */
    
    /*
    void OnLLMError(string errorMessage)
    {
        if (enableDebugLogs)
        {
            Debug.LogError($"[LLMGameController] LLM Error: {errorMessage}");
        }
        
        // エラー発生時も処理を続行
        isProcessingCommand = false;
    }
    */
    
    /*
    void OnLLMConnected()
    {
        if (enableDebugLogs)
        {
            Debug.Log("[LLMGameController] LLM Backend connected");
        }
    }
    */
    
    /*
    void OnLLMDisconnected()
    {
        if (enableDebugLogs)
        {
            Debug.LogWarning("[LLMGameController] LLM Backend disconnected");
        }
    }
    */
    
    void StartLLMControl()
    {
        if (isRunning)
        {
            if (enableDebugLogs)
            {
                Debug.Log("[LLMGameController] LLM control already running");
            }
            return;
        }
        
        isRunning = true;
        StartCoroutine(LLMControlLoop());
        
        if (enableDebugLogs)
        {
            Debug.Log("[LLMGameController] LLM control started");
        }
    }
    
    void StopLLMControl()
    {
        isRunning = false;
        
        if (enableDebugLogs)
        {
            Debug.Log("[LLMGameController] LLM control stopped");
        }
    }
    
    IEnumerator LLMControlLoop()
    {
        while (isRunning)
        {
            yield return new WaitForSeconds(logCheckInterval);
            
            // 定期的にログを処理（状況報告がない場合のフォールバック）
            if (logsSinceLastSituation.Count > 0 && !isProcessingCommand)
            {
                // 最後のログから一定時間経過している場合
                if (Time.time - Time.realtimeSinceStartup > logCheckInterval)
                {
                    ProcessLogsWithLLM();
                }
            }
        }
    }
    
    void SaveLogToFile(string logMessage)
    {
        try
        {
            string timestamp = System.DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
            string logEntry = $"[{timestamp}] {logMessage}\n";
            
            File.AppendAllText(logFilePath, logEntry);
        }
        catch (System.Exception e)
        {
            Debug.LogError($"[LLMGameController] Failed to save log to file: {e.Message}");
        }
    }
    
    // Public methods for external control
    
    public void TestLLMConnection()
    {
        if (llmCommunicator != null)
        {
            // 新しいLLMCommunicatorシステムでは、テスト用メソッドが変更されています
            llmCommunicator.SendManualLog("Unity LLM Controller test message");
            
            // テスト実行の詳細ログを削除
        }
        else
        {
            if (enableDebugLogs)
            {
                Debug.LogError("[LLMGameController] LLMCommunicator が見つかりません");
            }
        }
    }
    
    public void ForceProcessCurrentLogs()
    {
        // 新しいLLMCommunicatorシステムでは自動的にログが処理されます
        // 手動でのログ処理は不要になりました
        
        // 冗長なログを削除
    }
    
    public void ClearLogHistory()
    {
        gameLogHistory.Clear();
        logsSinceLastSituation.Clear();
        
        if (enableDebugLogs)
        {
            Debug.Log("[LLMGameController] Log history cleared");
        }
    }
    
    public List<string> GetRecentLogs(int count = 10)
    {
        return gameLogHistory.TakeLast(count).ToList();
    }
    
    public void EmergencyStop()
    {
        StopLLMControl();
        commandExecutor.StopCurrentCommand();
        isProcessingCommand = false;
        waitingForCommandResult = false;
        
        if (enableDebugLogs)
        {
            Debug.Log("[LLMGameController] Emergency stop executed");
        }
    }
    
    // コマンド実行後の結果待機
    IEnumerator WaitForCommandResult()
    {
        waitingForCommandResult = true;
        commandExecutionStartTime = Time.time;
        logsForNextCycle.Clear();
        
        if (enableDebugLogs)
        {
            Debug.Log("[LLMGameController] Waiting for command result...");
        }
        
        // コマンド実行完了まで待機
        yield return new WaitUntil(() => !commandExecutor.IsExecutingCommand());
        
        if (enableDebugLogs)
        {
            Debug.Log("[LLMGameController] Command execution completed, waiting for situation update...");
        }
        
        // 追加の待機時間（状況の変化が反映されるまで）
        yield return new WaitForSeconds(postCommandWaitTime);
        
        // AccessibilityNarratorが状況を更新するまで待機（最大タイムアウト時間）
        float startTime = Time.time;
        while (Time.time - startTime < commandExecutionTimeout)
        {
            if (logsForNextCycle.Count > 0)
            {
                // 新しいログが取得できた場合、処理を開始
                break;
            }
            yield return new WaitForSeconds(0.1f);
        }
        
        if (Time.time - startTime >= commandExecutionTimeout)
        {
            if (enableDebugLogs)
            {
                Debug.LogWarning("[LLMGameController] Command result timeout, forcing situation update");
            }
            // タイムアウトした場合、強制的に状況を更新
            ForceProcessCurrentLogs();
        }
    }
    
    // コマンド実行結果のログをLLMに送信
    IEnumerator ProcessCommandResultLogs()
    {
        // 冗長なログを削除
        
        // 結果待機状態を解除
        waitingForCommandResult = false;
        
        // 新しいLLMCommunicatorシステムでは自動的にログが処理されます
        // 手動でのログ送信は不要になりました
        if (logsForNextCycle.Count > 0)
        {
            // 詳細ログを削除
            
            // 次のサイクルの準備
            logsSinceLastSituation = new List<string>(logsForNextCycle);
            logsForNextCycle.Clear();
        }
        
        yield return null;
    }
    
    void OnDestroy()
    {
        // イベントリスナーを解除
        Application.logMessageReceived -= OnLogMessageReceived;
        
        // 新しいLLMCommunicatorは自動的にリソースを管理します
        // 手動でのイベント解除は不要になりました
        
        StopAllCoroutines();
    }
    
    // GUI for debugging
    void OnGUI()
    {
        if (!enableDebugLogs) return;
        
        GUILayout.BeginArea(new Rect(10, 10, 350, 250));
        GUILayout.Label("LLM Game Controller", GUI.skin.box);
        
        GUILayout.Label($"Status: {(isRunning ? "Running" : "Stopped")}");
        GUILayout.Label($"Backend: 新しいシステム（自動接続）");
        GUILayout.Label($"Commands Executed: {totalCommandsExecuted}");
        GUILayout.Label($"Last Command: {lastExecutedCommand}");
        GUILayout.Label($"Logs in Queue: {logsSinceLastSituation.Count}");
        GUILayout.Label($"Waiting for Result: {waitingForCommandResult}");
        GUILayout.Label($"Processing Command: {isProcessingCommand}");
        GUILayout.Label($"Command Executing: {commandExecutor.IsExecutingCommand()}");
        
        GUILayout.EndArea();
    }
} 