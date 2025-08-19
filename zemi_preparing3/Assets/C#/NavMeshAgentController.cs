// ナビゲーションコントローラー
// - NavMeshAgentを使用して目的地に移動
// - 移動中のアニメーションを制御
// - 移動中かどうかを確認
// - 移動中の場合は、移動を停止

using UnityEngine;
using UnityEngine.AI;
using System.Collections;
using StarterAssets;

public class NavMeshAgentController : MonoBehaviour
{
    [Header("NavMesh Settings")]
    [Tooltip("Movement speed when navigating to target")]
    public float navigationSpeed = 3.5f;
    
    [Tooltip("Stopping distance from target")]
    public float stoppingDistance = 0.5f;
    
    [Tooltip("Rotation speed when navigating")]
    public float rotationSpeed = 120f;
    
    private NavMeshAgent _agent;
    private ThirdPersonController _thirdPersonController;
    private Animator _animator;
    private bool _isNavigating = false;
    private Vector3 _targetPosition;
    
    private int _animIDSpeed;
    private int _animIDMotionSpeed;
    
    void Start()
    {
        _agent = GetComponent<NavMeshAgent>();
        _thirdPersonController = GetComponent<ThirdPersonController>();
        _animator = GetComponent<Animator>();
        
        if (_agent == null)
        {
            _agent = gameObject.AddComponent<NavMeshAgent>();
        }
        
        _agent.speed = navigationSpeed;
        _agent.stoppingDistance = stoppingDistance;
        _agent.angularSpeed = rotationSpeed;
        
        _animIDSpeed = Animator.StringToHash("Speed");
        _animIDMotionSpeed = Animator.StringToHash("MotionSpeed");
        
        _agent.enabled = false;
    }
    
    void Update()
    {
        if (_isNavigating && _agent.enabled)
        {
            UpdateNavigation();
        }
    }
    
    public void NavigateToPosition(Vector3 targetPosition)
    {
        _targetPosition = targetPosition;
        StartNavigation();
    }
    
    public void NavigateToPosition(float x, float y, float z)
    {
        NavigateToPosition(new Vector3(x, y, z));
    }
    
    private void StartNavigation()
    {
        if (_thirdPersonController != null)
        {
            _thirdPersonController.enabled = false;
        }
        
        _agent.enabled = true;
        _isNavigating = true;
        
        if (NavMesh.SamplePosition(_targetPosition, out NavMeshHit hit, 5.0f, NavMesh.AllAreas))
        {
            _agent.SetDestination(hit.position);
            Debug.Log($"[NavMeshAgent] Navigating to position: {hit.position}");
        }
        else
        {
            Debug.LogWarning($"[NavMeshAgent] Target position {_targetPosition} is not on NavMesh");
            StopNavigation();
        }
    }
    
    private void UpdateNavigation()
    {
        if (!_agent.pathPending && _agent.remainingDistance <= _agent.stoppingDistance)
        {
            if (!_agent.hasPath || _agent.velocity.sqrMagnitude == 0f)
            {
                StopNavigation();
            }
        }
        
        if (_animator != null)
        {
            float speed = _agent.velocity.magnitude;
            _animator.SetFloat(_animIDSpeed, speed);
            _animator.SetFloat(_animIDMotionSpeed, speed > 0.1f ? 1f : 0f);
        }
    }
    
    public void StopNavigation()
    {
        _isNavigating = false;
        
        if (_agent != null && _agent.enabled)
        {
            _agent.ResetPath();
            _agent.enabled = false;
        }
        
        if (_thirdPersonController != null)
        {
            _thirdPersonController.enabled = true;
        }
        
        if (_animator != null)
        {
            _animator.SetFloat(_animIDSpeed, 0f);
            _animator.SetFloat(_animIDMotionSpeed, 0f);
        }
        
        Debug.Log("[NavMeshAgent] Navigation stopped");
    }
    
    public bool IsNavigating()
    {
        return _isNavigating;
    }
    
    public float GetRemainingDistance()
    {
        if (_agent != null && _agent.enabled && _agent.hasPath)
        {
            return _agent.remainingDistance;
        }
        return 0f;
    }
}