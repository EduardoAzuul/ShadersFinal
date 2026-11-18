using System.Collections;
using UnityEngine;

/// <summary>
/// Spins this object a full 360 degrees after a delay. The spin lasts "spinDuration" seconds.
/// Call Play() from a Timeline Signal, a UnityEvent or another script, or enable playOnStart.
/// </summary>
public class DelayedSpin360 : MonoBehaviour
{
    [Header("Timing")]
    [SerializeField] private bool playOnStart = true;
    [Tooltip("Seconds to wait before the spin starts")]
    [SerializeField] private float delay = 2f;
    [Tooltip("Seconds the spin lasts")]
    [SerializeField] private float spinDuration = 3f;
    [Tooltip("Use unscaled time (ignores Time.timeScale)")]
    [SerializeField] private bool useUnscaledTime = false;

    [Header("Spin")]
    [Tooltip("Rotation axis")]
    [SerializeField] private Vector3 axis = Vector3.up;
    [Tooltip("Axis is relative to the object (local) or to the world")]
    [SerializeField] private Space space = Space.Self;
    [Tooltip("Easing over the spin: 0 -> 0 and 1 -> 360 degrees")]
    [SerializeField] private AnimationCurve curve = AnimationCurve.EaseInOut(0f, 0f, 1f, 1f);
    [Tooltip("Number of full turns (1 = 360 degrees)")]
    [SerializeField] private float turns = 1f;

    [Header("Repeat")]
    [SerializeField] private bool loop = false;
    [Tooltip("Seconds to wait between spins when looping")]
    [SerializeField] private float loopDelay = 1f;

    private Coroutine routine;

    private void Start()
    {
        if (playOnStart) Play();
    }

    public void Play()
    {
        if (routine != null) StopCoroutine(routine);
        routine = StartCoroutine(SpinRoutine());
    }

    public void Stop()
    {
        if (routine != null) StopCoroutine(routine);
        routine = null;
    }

    private IEnumerator SpinRoutine()
    {
        do
        {
            yield return Wait(delay);
            yield return Spin();

            if (loop) yield return Wait(loopDelay);
        }
        while (loop);

        routine = null;
    }

    private IEnumerator Wait(float seconds)
    {
        if (seconds <= 0f) yield break;

        float t = 0f;
        while (t < seconds)
        {
            t += DeltaTime();
            yield return null;
        }
    }

    private IEnumerator Spin()
    {
        Vector3 spinAxis = axis.sqrMagnitude > 0f ? axis.normalized : Vector3.up;
        float totalAngle = 360f * turns;
        float duration = Mathf.Max(spinDuration, 0.0001f);

        float applied = 0f; // Degrees already applied, so rotation is incremental and drift-free
        float t = 0f;

        while (t < 1f)
        {
            t = Mathf.Min(1f, t + DeltaTime() / duration);

            float target = curve.Evaluate(t) * totalAngle;
            transform.Rotate(spinAxis, target - applied, space);
            applied = target;

            yield return null;
        }

        // Make sure the final step lands exactly on the full turn count
        transform.Rotate(spinAxis, totalAngle - applied, space);
    }

    private float DeltaTime()
    {
        return useUnscaledTime ? Time.unscaledDeltaTime : Time.deltaTime;
    }
}
