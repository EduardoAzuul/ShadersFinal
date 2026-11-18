using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class CityVanishFinale : MonoBehaviour
{
    public enum WaveMode { Simultaneous, RadialFromOrigin, TopToBottom }

    [Header("Shader")]
    [Tooltip("Material using the Showcase/Dither Vanish shader, configured the way you like")]
    [SerializeField] private Material vanishTemplate;

    [Header("Timing")]
    [SerializeField] private bool playOnStart = false;
    [SerializeField] private float startDelay = 0f;
    [SerializeField] private float vanishDuration = 6f;
    [SerializeField] private AnimationCurve curve = AnimationCurve.EaseInOut(0f, 0f, 1f, 1f);

    [Header("City-wide wave")]
    [SerializeField] private WaveMode waveMode = WaveMode.RadialFromOrigin;
    [Tooltip("Where the vanish starts (Radial mode). Defaults to this object's position")]
    [SerializeField] private Transform waveOrigin;
    [Tooltip("0 = everything vanishes together, closer to 1 = a more marked wave")]
    [SerializeField, Range(0f, 0.9f)] private float waveSpread = 0.6f;

    [Header("End")]
    [SerializeField] private bool disableWhenDone = true;

    [Header("Debug")]
    [Tooltip("Logs the original materials where no albedo texture could be found")]
    [SerializeField] private bool logMissingTextures = true;

    private static readonly int VanishId = Shader.PropertyToID("_Vanish");

    // Property names that usually hold the main texture / color, in priority order
    private static readonly string[] TextureNames =
    {
        "_BaseMap", "_MainTex", "_BaseColorMap", "_Albedo", "_AlbedoMap",
        "_Diffuse", "_DiffuseMap", "_BaseTexture", "_Base_Map"
    };

    private static readonly string[] ColorNames =
    {
        "_BaseColor", "_Color", "_BaseTint", "_Tint"
    };

    // Texture properties that must never be used as albedo when scanning
    private static readonly string[] IgnoredTextureWords =
    {
        "bump", "normal", "metal", "occlusion", "emission", "emissive", "mask",
        "detail", "spec", "parallax", "height", "rough", "gloss", "lightmap", "shadowmask"
    };

    private struct Entry
    {
        public Renderer renderer;
        public float delay01; // 0 = vanishes first, 1 = vanishes last
    }

    private readonly List<Entry> entries = new();
    private readonly Dictionary<Renderer, Material[]> originalMaterials = new();
    private readonly Dictionary<Material, Material> vanishMaterials = new();
    private MaterialPropertyBlock block;
    private bool running;

    private void Start()
    {
        if (playOnStart) Play();
    }

    // Call this from a Timeline Signal, a UnityEvent, or any other script
    public void Play()
    {
        if (running) return;
        StartCoroutine(VanishRoutine());
    }

    private IEnumerator VanishRoutine()
    {
        running = true;

        if (startDelay > 0f) yield return new WaitForSeconds(startDelay);

        BuildEntries();
        ApplyVanish(0f);

        float t = 0f;
        while (t < 1f)
        {
            t += Time.deltaTime / vanishDuration;
            ApplyVanish(curve.Evaluate(Mathf.Clamp01(t)));
            yield return null;
        }

        ApplyVanish(1f);

        if (disableWhenDone)
        {
            // Some dither pixels can survive at exactly 1, so hide everything for good
            foreach (Entry e in entries)
            {
                if (e.renderer != null) e.renderer.enabled = false;
            }
        }

        running = false;
    }

    private void BuildEntries()
    {
        block ??= new MaterialPropertyBlock();
        entries.Clear();

        // MeshRenderer AND SkinnedMeshRenderer (animated characters), including inactive objects.
        // Overlays created by CityShaderTransition are skipped.
        Renderer[] renderers = System.Array.FindAll(
            GetComponentsInChildren<Renderer>(true),
            r => (r is MeshRenderer || r is SkinnedMeshRenderer) && !r.name.EndsWith("_CustomOverlay"));
        Vector3 origin = waveOrigin != null ? waveOrigin.position : transform.position;

        float[] metrics = new float[renderers.Length];
        float min = float.MaxValue;
        float max = float.MinValue;

        for (int i = 0; i < renderers.Length; i++)
        {
            Vector3 center = renderers[i].bounds.center;
            float metric = waveMode switch
            {
                WaveMode.RadialFromOrigin => Vector3.Distance(center, origin),
                WaveMode.TopToBottom => -center.y,
                _ => 0f
            };
            metrics[i] = metric;
            min = Mathf.Min(min, metric);
            max = Mathf.Max(max, metric);
        }

        float range = Mathf.Max(max - min, 1e-4f);

        for (int i = 0; i < renderers.Length; i++)
        {
            Renderer r = renderers[i];

            // Only store the originals once, so calling Play twice never overwrites them
            if (!originalMaterials.TryGetValue(r, out Material[] originals))
            {
                originals = r.sharedMaterials;
                originalMaterials[r] = originals;
            }

            Material[] swapped = new Material[originals.Length];
            for (int m = 0; m < originals.Length; m++)
            {
                swapped[m] = GetVanishMaterial(originals[m]);
            }
            r.sharedMaterials = swapped;

            entries.Add(new Entry { renderer = r, delay01 = (metrics[i] - min) / range });
        }
    }

    // One vanish material per original material, shared by every renderer that uses it
    private Material GetVanishMaterial(Material original)
    {
        if (original == null) return vanishTemplate;

        if (vanishMaterials.TryGetValue(original, out Material cached)) return cached;

        Material vanish = new Material(vanishTemplate);

        // Copy the original look: texture, tiling, offset and tint
        Texture tex = FindAlbedoTexture(original, out string texProp);

        // Always overwrite (even with null) so the template's own texture never leaks through
        vanish.SetTexture("_BaseMap", tex);

        if (tex != null)
        {
            vanish.SetTextureScale("_BaseMap", original.GetTextureScale(texProp));
            vanish.SetTextureOffset("_BaseMap", original.GetTextureOffset(texProp));
        }
        else if (logMissingTextures)
        {
            Debug.Log($"[CityVanishFinale] No albedo texture found on material '{original.name}' " +
                      $"(shader: {original.shader.name}). It will use a flat color.", original);
        }

        vanish.SetColor("_BaseColor", FindColor(original));

        vanishMaterials[original] = vanish;
        return vanish;
    }

    private static Texture FindAlbedoTexture(Material material, out string propertyName)
    {
        // 1) Well-known names
        foreach (string name in TextureNames)
        {
            if (!material.HasProperty(name)) continue;
            Texture t = material.GetTexture(name);
            if (t != null)
            {
                propertyName = name;
                return t;
            }
        }

        // 2) Shader Graph materials often use auto-generated names, so scan every texture slot
        foreach (string name in material.GetTexturePropertyNames())
        {
            if (IsIgnoredTexture(name)) continue;
            Texture t = material.GetTexture(name);
            if (t != null)
            {
                propertyName = name;
                return t;
            }
        }

        propertyName = null;
        return null;
    }

    private static bool IsIgnoredTexture(string propertyName)
    {
        string lower = propertyName.ToLowerInvariant();
        foreach (string word in IgnoredTextureWords)
        {
            if (lower.Contains(word)) return true;
        }
        return false;
    }

    private static Color FindColor(Material material)
    {
        foreach (string name in ColorNames)
        {
            if (material.HasProperty(name)) return material.GetColor(name);
        }
        return Color.white;
    }

    // progress: 0 = city fully visible, 1 = city fully gone
    private void ApplyVanish(float progress)
    {
        float spread = waveMode == WaveMode.Simultaneous ? 0f : waveSpread;

        foreach (Entry e in entries)
        {
            if (e.renderer == null) continue;

            // Each renderer starts a bit later depending on its delay
            float local = Mathf.Clamp01((progress - e.delay01 * spread) / (1f - spread));

            e.renderer.GetPropertyBlock(block);
            block.SetFloat(VanishId, local);
            e.renderer.SetPropertyBlock(block);
        }
    }

    // Handy for testing: brings the city back to how it was
    [ContextMenu("Reset City")]
    public void ResetCity()
    {
        StopAllCoroutines();
        running = false;

        foreach (var pair in originalMaterials)
        {
            if (pair.Key == null) continue;
            pair.Key.sharedMaterials = pair.Value;
            pair.Key.SetPropertyBlock(null);
            pair.Key.enabled = true;
        }

        foreach (Material m in vanishMaterials.Values) Destroy(m);
        vanishMaterials.Clear();
        originalMaterials.Clear();
        entries.Clear();
    }
}