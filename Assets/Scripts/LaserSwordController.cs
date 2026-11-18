using System.Collections;
using UnityEngine;
using UnityEngine.Events;

/// <summary>
/// Drives the _Vanish property of the "Showcase/Laser Sword Vanish" shader.
/// vanish = 1 -> blade fully retracted (off)
/// vanish = 0 -> blade fully extended (on)
/// Attach it to the sword blade (the object with the Renderer).
/// </summary>
[RequireComponent(typeof(Renderer))]
public class LaserSwordController : MonoBehaviour
{
    private static readonly int VanishId = Shader.PropertyToID("_Vanish");
    private static readonly int AutoAnimateId = Shader.PropertyToID("_AutoAnimate");

    [Header("Ignite")]
    [Tooltip("Seconds to wait before the blade starts to appear.")]
    [Min(0f)] public float igniteDelay = 1f;

    [Tooltip("Seconds the blade takes to go from fully off to fully on.")]
    [Min(0.01f)] public float igniteDuration = 0.6f;

    [Tooltip("Easing for the ignition. X = normalized time, Y = progress (0 to 1).")]
    public AnimationCurve igniteCurve = AnimationCurve.EaseInOut(0f, 0f, 1f, 1f);

    [Header("Extinguish")]
    [Min(0f)] public float extinguishDelay = 0f;
    [Min(0.01f)] public float extinguishDuration = 0.4f;
    public AnimationCurve extinguishCurve = AnimationCurve.EaseInOut(0f, 0f, 1f, 1f);

    [Header("Behaviour")]
    [Tooltip("Start the ignition automatically when the object is enabled.")]
    public bool igniteOnStart = true;

    [Tooltip("Ignore Time.timeScale (useful if the game gets paused or slowed down).")]
    public bool useUnscaledTime = false;

    [Header("Events")]
    public UnityEvent onIgnited;
    public UnityEvent onExtinguished;

    /// <summary>True once the blade is fully on.</summary>
    public bool IsOn { get; private set; }

    private Renderer _renderer;
    private MaterialPropertyBlock _block;
    private Coroutine _routine;
    private float _currentVanish = 1f;

    private void Awake()
    {
        _renderer = GetComponent<Renderer>();
        _block = new MaterialPropertyBlock();

        // The script takes control of vanish, so the shader's own auto animation must be off.
        // (If it is enabled on the material, it will override the value we set.)
        if (_renderer.sharedMaterial != null && _renderer.sharedMaterial.HasFloat(AutoAnimateId))
            _renderer.sharedMaterial.SetFloat(AutoAnimateId, 0f);

        // Start hidden so there is no flash before the delay is over.
        SetVanish(1f);
    }

    private void OnEnable()
    {
        if (igniteOnStart)
            Ignite();
    }

    /// <summary>Waits igniteDelay, then moves vanish from 1 to 0 over igniteDuration.</summary>
    [ContextMenu("Ignite")]
    public void Ignite()
    {
        StartTransition(0f, igniteDelay, igniteDuration, igniteCurve, true);
    }

    /// <summary>Waits extinguishDelay, then moves vanish from its current value to 1.</summary>
    [ContextMenu("Extinguish")]
    public void Extinguish()
    {
        StartTransition(1f, extinguishDelay, extinguishDuration, extinguishCurve, false);
    }

    /// <summary>Convenience for input callbacks: turns the sword on if it is off and vice versa.</summary>
    public void Toggle()
    {
        if (IsOn) Extinguish();
        else Ignite();
    }

    private void StartTransition(float target, float delay, float duration, AnimationCurve curve, bool turningOn)
    {
        if (_routine != null)
            StopCoroutine(_routine);

        _routine = StartCoroutine(Transition(target, delay, duration, curve, turningOn));
    }

    private IEnumerator Transition(float target, float delay, float duration, AnimationCurve curve, bool turningOn)
    {
        // Delay before the transition starts.
        if (delay > 0f)
        {
            if (useUnscaledTime) yield return new WaitForSecondsRealtime(delay);
            else yield return new WaitForSeconds(delay);
        }

        // Start from wherever the blade currently is, so interrupting mid-way looks smooth.
        float start = _currentVanish;
        float elapsed = 0f;

        // If the blade is already (almost) at the target, shorten the time proportionally.
        float distance = Mathf.Abs(target - start);
        float effectiveDuration = Mathf.Max(0.0001f, duration * Mathf.Max(distance, 0.0001f));

        while (elapsed < effectiveDuration)
        {
            elapsed += useUnscaledTime ? Time.unscaledDeltaTime : Time.deltaTime;
            float t = Mathf.Clamp01(elapsed / effectiveDuration);
            SetVanish(Mathf.Lerp(start, target, curve.Evaluate(t)));
            yield return null;
        }

        SetVanish(target);
        IsOn = turningOn;
        _routine = null;

        if (turningOn) onIgnited?.Invoke();
        else onExtinguished?.Invoke();
    }

    private void SetVanish(float value)
    {
        _currentVanish = value;
        _renderer.GetPropertyBlock(_block);
        _block.SetFloat(VanishId, value);
        _renderer.SetPropertyBlock(_block);
    }
}
