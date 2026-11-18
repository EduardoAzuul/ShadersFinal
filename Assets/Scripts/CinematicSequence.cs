using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Events;
using Unity.Cinemachine; // Cinemachine 3.x (Unity 6)

/// <summary>
/// Moves a CinemachineCamera along a Catmull-Rom spline defined by empty GameObjects.
/// Each waypoint defines how long it takes to arrive from the previous one,
/// how long to wait there, and (optionally) a target to look at and a FOV.
///
/// SETUP:
/// 1. Create a CinemachineCamera. Set its Position Control and Rotation Control to "None"
///    (this script drives its transform).
/// 2. Create an empty parent "CameraPath" with empty children ("Point 1", "Point 2", ...).
/// 3. Add this component (e.g. to the parent), drag the camera into "Cinemachine Camera",
///    then right-click the component header > "Fill Waypoints From Children".
/// 4. Tweak travel times in the Inspector. Move the empties in the Scene view:
///    the path is drawn live with gizmos.
/// </summary>
public class CinematicSequence : MonoBehaviour
{
    [System.Serializable]
    public class Waypoint
    {
        [Tooltip("Empty GameObject that marks the camera position (and rotation if no Look At is set).")]
        public Transform point;

        [Tooltip("Seconds it takes to travel from the previous waypoint to this one. Ignored on the first waypoint.")]
        [Min(0.01f)] public float travelTime = 3f;

        [Tooltip("Seconds the camera waits once it arrives here.")]
        [Min(0f)] public float holdTime = 0f;

        [Tooltip("Optional. If set, the camera looks at this object when at this waypoint. Otherwise it uses the rotation of the empty.")]
        public Transform lookAt;

        [Tooltip("Field of view at this waypoint. 0 = leave the camera FOV unchanged.")]
        [Min(0f)] public float fieldOfView = 0f;

        [Tooltip("Easing of the movement towards this waypoint (0 to 1 on both axes).")]
        public AnimationCurve easing = AnimationCurve.EaseInOut(0f, 0f, 1f, 1f);
    }

    [Header("References")]
    [SerializeField] private CinemachineCamera cinemachineCamera;

    [Header("Path")]
    [SerializeField] private List<Waypoint> waypoints = new List<Waypoint>();
    [SerializeField] private bool loop = false;

    [Header("Playback")]
    [SerializeField] private bool playOnStart = true;

    [Header("Events")]
    public UnityEvent onStarted;
    public UnityEvent onFinished;

    [Header("Gizmos")]
    [SerializeField] private Color pathColor = Color.cyan;
    [SerializeField] private int gizmoSamplesPerSegment = 20;

    private Coroutine running;

    public bool IsPlaying => running != null;

    private void Reset()
    {
        cinemachineCamera = FindFirstObjectByType<CinemachineCamera>();
    }

    private void Start()
    {
        if (playOnStart) Play();
    }

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    public void Play()
    {
        Stop();
        if (!IsValid()) return;
        running = StartCoroutine(PlayRoutine());
    }

    public void Stop()
    {
        if (running != null)
        {
            StopCoroutine(running);
            running = null;
        }
    }

    // ------------------------------------------------------------------
    // Playback
    // ------------------------------------------------------------------

    private IEnumerator PlayRoutine()
    {
        onStarted?.Invoke();

        do
        {
            // Snap to the first waypoint.
            ApplyPose(GetPosition(0), GetRotation(0, GetPosition(0)));
            ApplyFov(waypoints[0].fieldOfView);
            yield return Wait(waypoints[0].holdTime);

            // Travel through the rest of the waypoints.
            for (int i = 1; i < waypoints.Count; i++)
            {
                yield return MoveSegment(i - 1, i);
                yield return Wait(waypoints[i].holdTime);
            }
        }
        while (loop);

        running = null;
        onFinished?.Invoke();
    }

    private IEnumerator MoveSegment(int from, int to)
    {
        Waypoint target = waypoints[to];
        float duration = Mathf.Max(0.01f, target.travelTime);
        float elapsed = 0f;

        float startFov = GetCurrentFov();
        float endFov = target.fieldOfView > 0f ? target.fieldOfView : startFov;

        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;
            float k = target.easing.Evaluate(Mathf.Clamp01(elapsed / duration));

            // Position: Catmull-Rom spline through the waypoints.
            Vector3 position = CatmullRom(
                GetPosition(from - 1), GetPosition(from),
                GetPosition(to), GetPosition(to + 1), k);

            // Rotation: blend between the rotation at "from" and at "to".
            Quaternion rotation = Quaternion.Slerp(
                GetRotation(from, position), GetRotation(to, position), k);

            ApplyPose(position, rotation);
            ApplyFov(Mathf.Lerp(startFov, endFov, k));
            yield return null;
        }

        // Make sure we land exactly on the waypoint.
        ApplyPose(GetPosition(to), GetRotation(to, GetPosition(to)));
        ApplyFov(endFov);
    }

    private static IEnumerator Wait(float seconds)
    {
        if (seconds > 0f) yield return new WaitForSeconds(seconds);
    }

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    private Vector3 GetPosition(int index)
    {
        // Clamping duplicates the end points, so the spline starts/ends smoothly.
        // With loop enabled the path wraps around for a seamless curve.
        int count = waypoints.Count;
        index = loop ? (index % count + count) % count : Mathf.Clamp(index, 0, count - 1);
        return waypoints[index].point.position;
    }

    private Quaternion GetRotation(int index, Vector3 fromPosition)
    {
        Waypoint wp = waypoints[Mathf.Clamp(index, 0, waypoints.Count - 1)];
        if (wp.lookAt != null)
        {
            Vector3 dir = wp.lookAt.position - fromPosition;
            if (dir.sqrMagnitude > 0.0001f) return Quaternion.LookRotation(dir, Vector3.up);
        }
        return wp.point.rotation;
    }

    private static Vector3 CatmullRom(Vector3 p0, Vector3 p1, Vector3 p2, Vector3 p3, float t)
    {
        float t2 = t * t;
        float t3 = t2 * t;
        return 0.5f * (
            2f * p1 +
            (-p0 + p2) * t +
            (2f * p0 - 5f * p1 + 4f * p2 - p3) * t2 +
            (-p0 + 3f * p1 - 3f * p2 + p3) * t3);
    }

    private void ApplyPose(Vector3 position, Quaternion rotation)
    {
        cinemachineCamera.transform.SetPositionAndRotation(position, rotation);
    }

    private float GetCurrentFov()
    {
        return cinemachineCamera.Lens.FieldOfView;
    }

    private void ApplyFov(float fov)
    {
        if (fov <= 0f) return;
        var lens = cinemachineCamera.Lens;
        lens.FieldOfView = fov;
        cinemachineCamera.Lens = lens;
    }

    private bool IsValid()
    {
        if (cinemachineCamera == null)
        {
            Debug.LogError("CinematicSequence: no CinemachineCamera assigned.", this);
            return false;
        }
        if (waypoints.Count < 2)
        {
            Debug.LogError("CinematicSequence: at least 2 waypoints are required.", this);
            return false;
        }
        foreach (var wp in waypoints)
        {
            if (wp.point == null)
            {
                Debug.LogError("CinematicSequence: a waypoint has no point assigned.", this);
                return false;
            }
        }
        return true;
    }

    // ------------------------------------------------------------------
    // Editor conveniences
    // ------------------------------------------------------------------

    /// <summary>Fills the waypoint list with the children of this object, in hierarchy order.</summary>
    [ContextMenu("Fill Waypoints From Children")]
    private void FillWaypointsFromChildren()
    {
        waypoints.Clear();
        foreach (Transform child in transform)
        {
            waypoints.Add(new Waypoint { point = child });
        }
    }

    private void OnDrawGizmos()
    {
        if (waypoints == null || waypoints.Count == 0) return;

        // Waypoints with their forward direction.
        for (int i = 0; i < waypoints.Count; i++)
        {
            Transform p = waypoints[i].point;
            if (p == null) continue;

            Gizmos.color = Color.yellow;
            Gizmos.DrawWireSphere(p.position, 0.25f);
            Gizmos.color = Color.blue;
            Gizmos.DrawRay(p.position, p.forward * 0.8f);

            if (waypoints[i].lookAt != null)
            {
                Gizmos.color = Color.magenta;
                Gizmos.DrawLine(p.position, waypoints[i].lookAt.position);
            }

#if UNITY_EDITOR
            string label = i == 0 ? "#0 (start)" : $"#{i}  {waypoints[i].travelTime:0.##}s";
            UnityEditor.Handles.Label(p.position + Vector3.up * 0.4f, label);
#endif
        }

        // Spline preview.
        for (int p = 0; p < waypoints.Count; p++)
            if (waypoints[p].point == null) return;

        Gizmos.color = pathColor;
        int segments = loop ? waypoints.Count : waypoints.Count - 1;
        int samples = Mathf.Max(2, gizmoSamplesPerSegment);

        for (int s = 0; s < segments; s++)
        {
            Vector3 prev = GetPosition(s);
            for (int n = 1; n <= samples; n++)
            {
                float t = n / (float)samples;
                Vector3 next = CatmullRom(GetPosition(s - 1), GetPosition(s), GetPosition(s + 1), GetPosition(s + 2), t);
                Gizmos.DrawLine(prev, next);
                prev = next;
            }
        }
    }
}
