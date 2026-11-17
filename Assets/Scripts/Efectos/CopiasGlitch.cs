using UnityEngine;

/// <summary>
/// Mantiene las copias glitch (materiales CopiaGlitch) sincronizadas con el material principal
/// (PowerUpRetro, el primero del renderer): copia la onda, el glitch, el giro/flotar y el jitter
/// a un MaterialPropertyBlock del renderer, que afecta a todos sus materiales.
/// Así las copias se deforman exactamente igual que el objeto sin igualar valores a mano.
/// Uso: MeshRenderer → Materials = [M_PowerUpRetro, M_CopiaGlitch_Magenta, M_CopiaGlitch_Cian].
/// </summary>
[ExecuteAlways]
[RequireComponent(typeof(Renderer))]
public class CopiasGlitch : MonoBehaviour
{
    static readonly string[] Compartidas =
    {
        "_AlturaMin", "_AlturaMax", "_VelocidadRefresco", "_AnchoRefresco", "_AmplitudOnda", "_Ondulacion", "_InfladoSuave",
        "_FranjasGlitch", "_FPSGlitch", "_ProbabilidadGlitch", "_FuerzaGlitch",
        "_VelocidadGiro", "_AlturaFlotar", "_VelocidadFlotar", "_ResolucionJitter", "_Jitter",
    };
    static int[] ids;

    Renderer rend;
    MaterialPropertyBlock bloque;

    void OnEnable() => Aplicar();
    void OnValidate() => Aplicar();
    void LateUpdate() => Aplicar();   // así sigue los cambios del material en vivo

    void Aplicar()
    {
        if (rend == null) rend = GetComponent<Renderer>();
        if (rend == null) return;
        Material principal = rend.sharedMaterial;   // el primer material
        if (principal == null) return;

        if (ids == null)
        {
            ids = new int[Compartidas.Length];
            for (int i = 0; i < Compartidas.Length; i++) ids[i] = Shader.PropertyToID(Compartidas[i]);
        }
        bloque ??= new MaterialPropertyBlock();
        rend.GetPropertyBlock(bloque);   // conserva lo que pongan otros scripts (p. ej. DesvanecerEfecto)
        foreach (int id in ids)
            if (principal.HasFloat(id)) bloque.SetFloat(id, principal.GetFloat(id));
        rend.SetPropertyBlock(bloque);
    }
}
