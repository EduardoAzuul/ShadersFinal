using UnityEditor;
using UnityEngine;

public static class ConvertStandardToURP
{
    [MenuItem("Tools/Convert Standard Materials To URP")]
    private static void Convert()
    {
        Shader urpLit = Shader.Find("Universal Render Pipeline/Lit");
        string[] guids = AssetDatabase.FindAssets("t:Material");
        int converted = 0;

        foreach (string guid in guids)
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            Material m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null || !path.EndsWith(".mat")) continue;

            string shaderName = m.shader.name;
            bool isStandard = shaderName == "Standard";
            bool isSpecular = shaderName == "Standard (Specular setup)";
            if (!isStandard && !isSpecular) continue;

            // Read the old values BEFORE swapping the shader
            Texture albedo = m.GetTexture("_MainTex");
            Color color = m.GetColor("_Color");
            Texture normal = m.GetTexture("_BumpMap");
            float smoothness = m.HasProperty("_Glossiness") ? m.GetFloat("_Glossiness") : 0.5f;
            float metallic = m.HasProperty("_Metallic") ? m.GetFloat("_Metallic") : 0f;
            Color specColor = m.HasProperty("_SpecColor") ? m.GetColor("_SpecColor") : Color.gray;
            Vector2 tiling = m.GetTextureScale("_MainTex");
            Vector2 offset = m.GetTextureOffset("_MainTex");

            m.shader = urpLit;

            m.SetTexture("_BaseMap", albedo);
            m.SetColor("_BaseColor", color);
            m.SetTextureScale("_BaseMap", tiling);
            m.SetTextureOffset("_BaseMap", offset);
            m.SetFloat("_Smoothness", smoothness);

            if (isSpecular)
            {
                // Switch URP/Lit to the Specular workflow
                m.SetFloat("_WorkflowMode", 0f);
                m.SetColor("_SpecColor", specColor);
                m.EnableKeyword("_SPECULAR_SETUP");
            }
            else
            {
                m.SetFloat("_Metallic", metallic);
            }

            if (normal != null)
            {
                m.SetTexture("_BumpMap", normal);
                m.EnableKeyword("_NORMALMAP");
            }

            EditorUtility.SetDirty(m);
            converted++;
        }

        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Debug.Log($"Converted {converted} materials to URP/Lit.");
    }
}