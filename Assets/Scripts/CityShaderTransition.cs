using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

/// <summary>
/// Crossfades from a custom look (e.g. the Blueprint shader) to the original materials.
/// The original renderers are NOT touched. For each MeshRenderer a child overlay is created
/// that draws the same mesh with the custom material. The overlay dissolves with a dither
/// pattern driven by the global _CityBlend (1 = fully custom, 0 = fully original).
/// The custom shader must read the global _CityBlend and clip with it (see the Blueprint notes).
/// </summary>
[DefaultExecutionOrder(-100)] // Run before other scripts so the first frame is already custom
public class CityShaderTransition : MonoBehaviour
{
    [Header("Custom look")]
    [Tooltip("Preferred: a material using your custom shader, so you can tweak its colors and density.")]
    [SerializeField] private Material customMaterial;

    [Tooltip("Used only if no material is assigned above.")]
    [SerializeField] private Shader customShader;

    [Tooltip("Copy texture/color properties from each original material into the overlay. " +
             "Keep it OFF for procedural shaders like Blueprint: shared names such as _BaseColor " +
             "would overwrite the shader's own colors.")]
    [SerializeField] private bool copyOriginalProperties = false;

    [Header("Extra objects")]
    [Tooltip("Objects that are NOT children of this object but must also get the effect " +
             "(e.g. a prop or effect object placed outside the City hierarchy).")]
    [SerializeField] private Transform[] extraRoots;

    [Header("Debug")]
    [Tooltip("Logs every renderer that could not get an overlay, and why.")]
    [SerializeField] private bool logSkipped = true;

    [Header("Timing")]
    [SerializeField] private float holdTime = 2f;
    [SerializeField] private float fadeTime = 5f;
    [SerializeField] private AnimationCurve curve = AnimationCurve.EaseInOut(0f, 1f, 1f, 0f);

    private static readonly int CityBlendId = Shader.PropertyToID("_CityBlend");
    private static readonly int CityDissolveId = Shader.PropertyToID("_CityDissolve");
    private static readonly int OffsetFactorId = Shader.PropertyToID("_OffsetFactor");
    private static readonly int OffsetUnitsId = Shader.PropertyToID("_OffsetUnits");
    private static readonly int BaseMapId = Shader.PropertyToID("_BaseMap");
    private static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");

    // Texture slots that must never be used as albedo when scanning a foreign material
    private static readonly string[] IgnoredTextureWords =
    {
        "bump", "normal", "metal", "occlusion", "emission", "emissive", "mask",
        "detail", "spec", "parallax", "height", "rough", "gloss", "lightmap", "shadowmask"
    };

    private struct OverlayPair
    {
        public Renderer source;
        public Renderer overlay;
    }

    private readonly List<OverlayPair> pairs = new();
    private readonly List<GameObject> overlays = new();
    private readonly List<Material> createdMaterials = new();

    private void Awake()
    {
        // Set the blend before the first rendered frame so the default look never shows up
        Shader.SetGlobalFloat(CityBlendId, 1f);
        CreateOverlays();
    }

    private void Start()
    {
        StartCoroutine(TransitionRoutine());
    }

    private IEnumerator TransitionRoutine()
    {
        yield return new WaitForSeconds(holdTime);

        float t = 0f;
        while (t < 1f)
        {
            t += Time.deltaTime / fadeTime;
            Shader.SetGlobalFloat(CityBlendId, curve.Evaluate(Mathf.Clamp01(t)));
            yield return null;
        }

        Shader.SetGlobalFloat(CityBlendId, 0f);
        DestroyOverlays();
    }

    private Material CreateCustomMaterial()
    {
        if (customMaterial != null) return new Material(customMaterial);
        if (customShader != null) return new Material(customShader);

        Debug.LogError("[CityShaderTransition] Assign a custom material or shader.", this);
        return null;
    }

    private void CreateOverlays()
    {
        // Renderer (not just MeshRenderer) so animated characters (SkinnedMeshRenderer) are included.
        // includeInactive = true so objects that a sequence activates later also get their overlay.
        List<Renderer> renderers = new(GetComponentsInChildren<Renderer>(true));
        if (extraRoots != null)
        {
            foreach (Transform root in extraRoots)
            {
                if (root == null) continue;
                foreach (Renderer r in root.GetComponentsInChildren<Renderer>(true))
                {
                    if (!renderers.Contains(r)) renderers.Add(r);
                }
            }
        }

        foreach (Renderer source in renderers)
        {
            SkinnedMeshRenderer skinned = source as SkinnedMeshRenderer;
            MeshRenderer meshRenderer = source as MeshRenderer;
            if (skinned == null && meshRenderer == null)
            {
                // Particles, trails, lines... cannot be duplicated as a mesh overlay
                if (logSkipped)
                    Debug.LogWarning($"[CityShaderTransition] Skipped '{PathOf(source)}': " +
                                     $"{source.GetType().Name} is not a mesh renderer.", source);
                continue;
            }
            if (source.name.EndsWith("_CustomOverlay")) continue;

            Mesh mesh;
            if (skinned != null)
            {
                mesh = skinned.sharedMesh;
            }
            else
            {
                MeshFilter sourceFilter = source.GetComponent<MeshFilter>();
                mesh = sourceFilter != null ? sourceFilter.sharedMesh : null;
            }
            if (mesh == null)
            {
                if (logSkipped)
                    Debug.LogWarning($"[CityShaderTransition] Skipped '{PathOf(source)}': no mesh " +
                                     "(missing MeshFilter or empty mesh).", source);
                continue;
            }

            Material[] originals = source.sharedMaterials;

            // Transparent originals (queue >= 2500) are drawn AFTER the opaque queue, so an overlay
            // at Geometry+1 would be painted over by the original. Draw the overlay just after it.
            int overlayQueue = (int)RenderQueue.Geometry + 1;
            foreach (Material original in originals)
            {
                if (original != null) overlayQueue = Mathf.Max(overlayQueue, original.renderQueue + 1);
            }
            Material[] custom = new Material[originals.Length];
            for (int i = 0; i < originals.Length; i++)
            {
                Material m = CreateCustomMaterial();
                if (m == null) return;

                if (copyOriginalProperties && originals[i] != null)
                {
                    m.CopyPropertiesFromMaterial(originals[i]); // Works for URP/Lit and similar names
                    CopyAlbedoFallback(originals[i], m);        // Covers Shader Graph / Standard names
                }

                // Only used by shaders that expose them (the toon shader); ignored otherwise
                m.SetFloat(CityDissolveId, 1f);
                m.SetFloat(OffsetFactorId, -1f);
                m.SetFloat(OffsetUnitsId, -1f);

                // Draw right after the original opaque geometry, so at equal depth the overlay wins
                m.renderQueue = overlayQueue;

                custom[i] = m;
                createdMaterials.Add(m);
            }

            GameObject overlay = new GameObject(source.name + "_CustomOverlay");
            overlay.transform.SetParent(source.transform, false); // Same transform as the source

            Renderer overlayRenderer;
            if (skinned != null)
            {
                // Same mesh, same bones: it follows the animation of the original
                SkinnedMeshRenderer overlaySkinned = overlay.AddComponent<SkinnedMeshRenderer>();
                overlaySkinned.sharedMesh = skinned.sharedMesh;
                overlaySkinned.bones = skinned.bones;
                overlaySkinned.rootBone = skinned.rootBone;
                overlaySkinned.localBounds = skinned.localBounds;
                overlaySkinned.updateWhenOffscreen = skinned.updateWhenOffscreen;
                overlayRenderer = overlaySkinned;
            }
            else
            {
                overlay.AddComponent<MeshFilter>().sharedMesh = mesh;
                overlayRenderer = overlay.AddComponent<MeshRenderer>();
            }

            overlayRenderer.sharedMaterials = custom;
            overlayRenderer.shadowCastingMode = ShadowCastingMode.Off;
            overlayRenderer.receiveShadows = true;
            overlayRenderer.enabled = source.enabled; // do not reveal renderers that are hidden on purpose

            overlays.Add(overlay);
            pairs.Add(new OverlayPair { source = source, overlay = overlayRenderer });
        }
    }

    // Keeps every overlay in sync with its source: scripts, Timeline or Animator may toggle
    // Renderer.enabled or swap the mesh / bones after Awake, and a one-time copy would miss that.
    private void LateUpdate()
    {
        foreach (OverlayPair pair in pairs)
        {
            if (pair.overlay == null) continue;

            if (pair.source == null)
            {
                pair.overlay.enabled = false;
                continue;
            }

            pair.overlay.enabled = pair.source.enabled;

            if (pair.source is SkinnedMeshRenderer s && pair.overlay is SkinnedMeshRenderer o)
            {
                if (o.sharedMesh != s.sharedMesh) o.sharedMesh = s.sharedMesh;
                if (o.rootBone != s.rootBone) o.rootBone = s.rootBone;

                Transform[] sourceBones = s.bones;
                if (sourceBones.Length != o.bones.Length) o.bones = sourceBones;
            }
        }
    }

    // Right-click the component > "Log renderer report" (in Play mode) to see which renderers
    // have an overlay and which ones do not.
    [ContextMenu("Log renderer report")]
    private void LogRendererReport()
    {
        foreach (Renderer r in GetComponentsInChildren<Renderer>(true))
        {
            if (r.name.EndsWith("_CustomOverlay")) continue;

            bool covered = pairs.Exists(p => p.source == r);
            int queue = r.sharedMaterial != null ? r.sharedMaterial.renderQueue : -1;
            Debug.Log($"[CityShaderTransition] {(covered ? "OK     " : "MISSING")} {PathOf(r)} " +
                      $"({r.GetType().Name}, enabled={r.enabled}, active={r.gameObject.activeInHierarchy}, " +
                      $"queue={queue}, shader={(r.sharedMaterial != null ? r.sharedMaterial.shader.name : "none")})", r);
        }
    }

    private static string PathOf(Component c)
    {
        string path = c.name;
        for (Transform t = c.transform.parent; t != null; t = t.parent) path = t.name + "/" + path;
        return path;
    }

    // If CopyPropertiesFromMaterial did not bring a texture (different property names),
    // use the first albedo-like texture of the original material.
    private static void CopyAlbedoFallback(Material source, Material target)
    {
        if (!target.HasProperty(BaseMapId)) return;

        if (target.GetTexture(BaseMapId) == null)
        {
            foreach (string name in source.GetTexturePropertyNames())
            {
                if (IsIgnoredTexture(name)) continue;

                Texture tex = source.GetTexture(name);
                if (tex == null) continue;

                target.SetTexture(BaseMapId, tex);
                target.SetTextureScale(BaseMapId, source.GetTextureScale(name));
                target.SetTextureOffset(BaseMapId, source.GetTextureOffset(name));
                break;
            }
        }

        // Standard shader tint
        if (target.HasProperty(BaseColorId) && !source.HasProperty(BaseColorId) && source.HasProperty("_Color"))
            target.SetColor(BaseColorId, source.GetColor("_Color"));
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

    private void DestroyOverlays()
    {
        foreach (GameObject o in overlays)
            if (o != null) Destroy(o);

        foreach (Material m in createdMaterials)
            if (m != null) Destroy(m);

        overlays.Clear();
        pairs.Clear();
        createdMaterials.Clear();
    }

    private void OnDestroy()
    {
        DestroyOverlays();
    }
}
