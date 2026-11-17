using System.Collections;
using UnityEngine;

/// <summary>
/// Controla el shader DitherVanish en este objeto:
///  - porcentaje (0-100 %): los agujeros crecen según la luz: en la sombra nacen antes y son más
///    grandes, en la luz son más chicos y llegan al final (100 % = el objeto desaparece entero).
///    "Retraso Luz" (_RetrasoLuz, en el material) decide cuánto después se borra la luz.
///  - anguloLuz (0-180°): hasta qué ángulo respecto a la luz se considera "luz".
///    180 = todo es luz, 0 = todo es sombra (invisible con porcentaje >= SombraCompleta).
/// Usa un MaterialPropertyBlock: cada objeto tiene sus propios valores sin copiar el material.
/// Los campos se pueden animar con Animator/Timeline, o usar SwooshDesaparecer()/SwooshAparecer().
/// </summary>
[ExecuteAlways]
[RequireComponent(typeof(Renderer))]
public class DesvanecerEfecto : MonoBehaviour
{
    static readonly int IdDesvanecer = Shader.PropertyToID("_Desvanecer");
    static readonly int IdAnguloLuz = Shader.PropertyToID("_AnguloLuz");
    static readonly int IdRetrasoLuz = Shader.PropertyToID("_RetrasoLuz");

    /// <summary>Porcentaje con el que la zona en sombra ya está borrada del todo:
    /// 100 / (1 + Retraso Luz) según el material (50 % si no tiene la propiedad).</summary>
    public float SombraCompleta
    {
        get
        {
            if (rend == null) rend = GetComponent<Renderer>();
            Material m = rend != null ? rend.sharedMaterial : null;
            if (m == null || !m.HasFloat(IdRetrasoLuz)) return 50f;
            return 100f / (1f + Mathf.Max(0f, m.GetFloat(IdRetrasoLuz)));
        }
    }

    [Range(0f, 100f)]
    [Tooltip("0 = nada, 100 = se borra todo el objeto. La sombra se va primero (agujeros grandes) y la luz al final (agujeros chicos)")]
    public float porcentaje = 0f;

    [Range(0f, 180f)]
    [Tooltip("Ángulo máximo respecto a la luz que cuenta como 'luz'. 180 = todo visible, 0 = todo en sombra")]
    public float anguloLuz = 90f;

    [Tooltip("Curva del swoosh (estilo cartoon: arranca lento y termina rápido)")]
    public AnimationCurve curvaSwoosh = new AnimationCurve(
        new Keyframe(0f, 0f, 0f, 0f), new Keyframe(1f, 1f, 2.5f, 0f));

    [Tooltip("Duración (segundos) usada por los botones de prueba del menú contextual")]
    public float duracionPrueba = 0.6f;

    Renderer rend;
    MaterialPropertyBlock bloque;
    Coroutine animacion;

    void OnEnable() => Aplicar();
    void OnValidate() => Aplicar();
    void LateUpdate() => Aplicar();   // así funciona aunque un Animator cambie los campos

    void Aplicar()
    {
        if (rend == null) rend = GetComponent<Renderer>();
        if (rend == null) return;
        bloque ??= new MaterialPropertyBlock();
        rend.GetPropertyBlock(bloque);
        bloque.SetFloat(IdDesvanecer, Mathf.Clamp(porcentaje, 0f, 100f));
        bloque.SetFloat(IdAnguloLuz, Mathf.Clamp(anguloLuz, 0f, 180f));
        rend.SetPropertyBlock(bloque);
    }

    /// <summary>Swoosh: la sombra barre el objeto (180° → 0°) hasta que desaparece.</summary>
    public void SwooshDesaparecer(float duracion)
    {
        porcentaje = SombraCompleta;
        Animar(SombraCompleta, 0f, duracion);
    }

    /// <summary>Swoosh inverso: el objeto aparece desde el lado iluminado (0° → 180°).</summary>
    public void SwooshAparecer(float duracion)
    {
        porcentaje = SombraCompleta;
        Animar(SombraCompleta, 180f, duracion);
    }

    /// <summary>Solo borra / restaura la zona en sombra, sin mover el ángulo.</summary>
    public void DesvanecerSombra(float duracion) => Animar(SombraCompleta, anguloLuz, duracion);
    public void RestaurarSombra(float duracion) => Animar(0f, anguloLuz, duracion);

    /// <summary>Borra el objeto entero (primero la sombra, luego la luz), sin mover el ángulo.</summary>
    public void DesvanecerTodo(float duracion) => Animar(100f, anguloLuz, duracion);

    /// <summary>Anima porcentaje y ángulo hasta los valores destino en "duracion" segundos.</summary>
    public void Animar(float destinoPorcentaje, float destinoAngulo, float duracion)
    {
        if (animacion != null) StopCoroutine(animacion);
        animacion = StartCoroutine(Rutina(Mathf.Clamp(destinoPorcentaje, 0f, 100f),
                                          Mathf.Clamp(destinoAngulo, 0f, 180f),
                                          Mathf.Max(0f, duracion)));
    }

    IEnumerator Rutina(float destinoPorcentaje, float destinoAngulo, float duracion)
    {
        float p0 = porcentaje, a0 = anguloLuz;
        for (float t = 0f; t < duracion; t += Time.deltaTime)
        {
            float k = curvaSwoosh.Evaluate(t / duracion);
            porcentaje = Mathf.LerpUnclamped(p0, destinoPorcentaje, k);
            anguloLuz = Mathf.LerpUnclamped(a0, destinoAngulo, k);
            yield return null;
        }
        porcentaje = destinoPorcentaje;
        anguloLuz = destinoAngulo;
        animacion = null;
    }

    [ContextMenu("Probar: Swoosh desaparecer")]
    void ProbarSwooshDesaparecer() { if (Application.isPlaying) SwooshDesaparecer(duracionPrueba); }

    [ContextMenu("Probar: Swoosh aparecer")]
    void ProbarSwooshAparecer() { if (Application.isPlaying) SwooshAparecer(duracionPrueba); }

    [ContextMenu("Probar: Desvanecer sombra")]
    void ProbarDesvanecerSombra() { if (Application.isPlaying) DesvanecerSombra(duracionPrueba); }

    [ContextMenu("Probar: Desvanecer todo")]
    void ProbarDesvanecerTodo() { if (Application.isPlaying) DesvanecerTodo(duracionPrueba); }

    [ContextMenu("Probar: Restaurar sombra")]
    void ProbarRestaurarSombra() { if (Application.isPlaying) RestaurarSombra(duracionPrueba); }
}
