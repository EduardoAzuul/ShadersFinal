using System.Collections;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.SceneManagement;

/// <summary>
/// Ends the scene after "endTime" seconds. Depending on "endAction" it stops Play mode / quits the
/// build, loads another scene, or only fires the UnityEvent (e.g. to start a fade or show credits).
/// </summary>
public class EndSceneTimer : MonoBehaviour
{
    public enum EndAction { QuitApplication, LoadScene, EventOnly }

    [Header("Timing")]
    [Tooltip("Seconds from Start until the scene ends")]
    [SerializeField] private float endTime = 120f;
    [SerializeField] private bool startOnStart = true;
    [Tooltip("Use unscaled time (ignores Time.timeScale)")]
    [SerializeField] private bool useUnscaledTime = false;

    [Header("What happens at the end")]
    [SerializeField] private EndAction endAction = EndAction.QuitApplication;
    [Tooltip("Used only by LoadScene. The scene must be added in File > Build Settings")]
    [SerializeField] private string sceneToLoad = "";

    [Header("Optional fade to black")]
    [Tooltip("Seconds of fade-out BEFORE endTime is reached. 0 = no fade")]
    [SerializeField] private float fadeDuration = 0f;
    [SerializeField] private Color fadeColor = Color.black;

    [Header("Event")]
    [Tooltip("Invoked right before the end action runs")]
    [SerializeField] private UnityEvent onEnd;

    private Coroutine routine;
    private float fadeAlpha;
    private Texture2D fadeTexture;

    private void Start()
    {
        if (startOnStart) Begin();
    }

    // Call this from a Timeline Signal or another script if startOnStart is off
    public void Begin()
    {
        if (routine != null) StopCoroutine(routine);
        routine = StartCoroutine(EndRoutine());
    }

    public void Cancel()
    {
        if (routine != null) StopCoroutine(routine);
        routine = null;
        fadeAlpha = 0f;
    }

    private IEnumerator EndRoutine()
    {
        float fade = Mathf.Clamp(fadeDuration, 0f, endTime);
        float t = 0f;

        while (t < endTime)
        {
            t += useUnscaledTime ? Time.unscaledDeltaTime : Time.deltaTime;

            if (fade > 0f)
                fadeAlpha = Mathf.Clamp01((t - (endTime - fade)) / fade);

            yield return null;
        }

        fadeAlpha = fade > 0f ? 1f : 0f;
        onEnd?.Invoke();
        routine = null;

        switch (endAction)
        {
            case EndAction.QuitApplication:
                QuitApp();
                break;

            case EndAction.LoadScene:
                if (string.IsNullOrEmpty(sceneToLoad))
                    Debug.LogError("[EndSceneTimer] sceneToLoad is empty.", this);
                else
                    SceneManager.LoadScene(sceneToLoad);
                break;
        }
    }

    private static void QuitApp()
    {
#if UNITY_EDITOR
        UnityEditor.EditorApplication.isPlaying = false; // Stops Play mode in the editor
#else
        Application.Quit();
#endif
    }

    // Simple full-screen fade, no Canvas needed
    private void OnGUI()
    {
        if (fadeAlpha <= 0f) return;

        if (fadeTexture == null)
        {
            fadeTexture = new Texture2D(1, 1);
            fadeTexture.SetPixel(0, 0, Color.white);
            fadeTexture.Apply();
        }

        Color previous = GUI.color;
        GUI.color = new Color(fadeColor.r, fadeColor.g, fadeColor.b, fadeAlpha);
        GUI.DrawTexture(new Rect(0f, 0f, Screen.width, Screen.height), fadeTexture);
        GUI.color = previous;
    }

    private void OnDestroy()
    {
        if (fadeTexture != null) Destroy(fadeTexture);
    }
}
