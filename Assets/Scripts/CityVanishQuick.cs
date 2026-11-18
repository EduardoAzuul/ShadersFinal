using System.Collections;
using UnityEngine;

/// <summary>
/// Standalone script that only animates _Vanish on renderers that ALREADY use the vanish material.
/// It does not swap materials or touch textures. Put it on the city root (or any parent)
/// and it drives every child Renderer through a MaterialPropertyBlock, so the material
/// asset is never modified.
/// </summary>
public class CityVanishQuick : MonoBehaviour
{
    [Header("Values")]
    [Tooltip("_Vanish value at the start (0 = visible, 1 = gone)")]
    [Range(0f, 1f)] public float from = 0f;

    [Tooltip("_Vanish value at the end")]
    [Range(0f, 1f)] public float to = 1f;

    [Header("Timing")]
    [Min(0f)] public float delay = 0f;
    [Min(0.01f)] public float duration = 1f;
    public AnimationCurve curve = AnimationCurve.EaseInOut(0f, 0f, 1f, 1f);

    [Header("Behaviour")]
    public bool playOnStart = false;
    [Tooltip("Disable the renderers once the vanish reaches 1 (hides leftover dither pixels)")]
    public bool disableRenderersAtEnd = true;

    private static readonly int VanishId = Shader.PropertyToID("_Vanish");

    private Renderer[] _renderers;
    private MaterialPropertyBlock _block;
    private Coroutine _routine;

    private void Awake()
    {
        _renderers = GetComponentsInChildren<Renderer>();
        _block = new MaterialPropertyBlock();
    }

    private void Start()
    {
        if (playOnStart) Play();
    }

    /// <summary>Plays from "from" to "to". Call it from a Timeline Signal, UnityEvent or another script.</summary>
    [ContextMenu("Play")]
    public void Play()
    {
        Restart(from, to);
    }

    /// <summary>Plays the opposite direction (brings the city back).</summary>
    [ContextMenu("Play Reverse")]
    public void PlayReverse()
    {
        Restart(to, from);
    }

    /// <summary>Sets _Vanish instantly on every renderer.</summary>
    public void SetVanish(float value)
    {
        foreach (Renderer r in _renderers)
        {
            if (r == null) continue;
            r.enabled = true;
            r.GetPropertyBlock(_block);
            _block.SetFloat(VanishId, value);
            r.SetPropertyBlock(_block);
        }
    }

    private void Restart(float a, float b)
    {
        if (_renderers == null) Awake();
        if (_routine != null) StopCoroutine(_routine);
        _routine = StartCoroutine(Animate(a, b));
    }

    private IEnumerator Animate(float a, float b)
    {
        if (delay > 0f) yield return new WaitForSeconds(delay);

        float t = 0f;
        while (t < 1f)
        {
            t += Time.deltaTime / duration;
            SetVanish(Mathf.Lerp(a, b, curve.Evaluate(Mathf.Clamp01(t))));
            yield return null;
        }

        SetVanish(b);

        if (disableRenderersAtEnd && b >= 1f)
        {
            foreach (Renderer r in _renderers)
                if (r != null) r.enabled = false;
        }

        _routine = null;
    }
}
