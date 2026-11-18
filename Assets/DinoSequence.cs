using System.Collections;
using System.Collections.Generic;
using UnityEngine;

// Names match the parameters of the Dinosaur Animator Controller
// (Attack, Jump, Beer, Hurt, Dead are triggers; Walk uses the "isRunning" bool).
public enum DinoAction
{
    Walk,
    Attack, // AttackRetraso -> AttackMordida -> AttackFinal
    Jump,
    Beer,
    Hurt,
    Dead
}

[System.Serializable]
public class DinoStep
{
    public DinoAction action = DinoAction.Walk;

    [Tooltip("Seconds to wait (in idle) BEFORE this action starts.")]
    [Min(0f)] public float delayBefore = 0f;

    [Tooltip("How long the action lasts, in seconds.\n" +
             "0 = let the animation finish by itself (not valid for Walk).")]
    [Min(0f)] public float duration = 0f;
}

/// <summary>
/// Plays a list of actions in order. Each step waits "delayBefore" seconds,
/// performs the action, and the dinosaur goes back to idle when it ends.
/// </summary>
[RequireComponent(typeof(Animator))]
public class DinoSequence : MonoBehaviour
{
    [Header("Sequence")]
    [SerializeField]
    private List<DinoStep> steps = new List<DinoStep>
    {
        // Example: after 10s walk for 3s, 1s later bite, then die.
        new DinoStep { action = DinoAction.Walk,   delayBefore = 10f, duration = 3f },
        new DinoStep { action = DinoAction.Attack, delayBefore = 1f,  duration = 0f },
        new DinoStep { action = DinoAction.Dead,   delayBefore = 0f,  duration = 0f },
    };

    [SerializeField] private bool playOnStart = true;
    [SerializeField] private bool loop = false;

    [Header("Animator names")]
    [SerializeField] private string idleState = "DinoIdle";
    [SerializeField] private string deadState = "Dead";
    [SerializeField] private string runningParam = "isRunning";

    [Header("Safety")]
    [Tooltip("Max seconds to wait for an animation that should end by itself.")]
    [SerializeField] private float maxWaitForAnimation = 30f;

    private const int Layer = 0;
    private static readonly string[] TriggerNames = { "Attack", "Jump", "Beer", "Hurt", "Dead" };

    private Animator animator;
    private int idleHash;
    private int deadHash;
    private Coroutine running;

    private void Awake()
    {
        animator = GetComponent<Animator>();
        idleHash = Animator.StringToHash(idleState);
        deadHash = Animator.StringToHash(deadState);
    }

    private void Start()
    {
        if (playOnStart)
            StartSequence();
    }

    /// <summary>Starts (or restarts) the sequence from the first step.</summary>
    public void StartSequence()
    {
        StopSequence();
        running = StartCoroutine(RunSequence());
    }

    /// <summary>Stops the sequence and returns the dinosaur to idle.</summary>
    public void StopSequence()
    {
        if (running != null)
        {
            StopCoroutine(running);
            running = null;
        }
        ForceIdle();
    }

    private IEnumerator RunSequence()
    {
        if (steps == null || steps.Count == 0)
            yield break;

        do
        {
            ForceIdle();

            foreach (DinoStep step in steps)
            {
                if (step.delayBefore > 0f)
                    yield return new WaitForSeconds(step.delayBefore);

                yield return RunStep(step);
            }

            yield return null; // avoids an infinite loop if every step takes zero time
        }
        while (loop);

        running = null;
    }

    private IEnumerator RunStep(DinoStep step)
    {
        // WALK: keep isRunning = true for the given duration
        if (step.action == DinoAction.Walk)
        {
            if (step.duration <= 0f)
            {
                Debug.LogWarning($"[{name}] Walk step needs a duration greater than 0. Skipped.", this);
                yield break;
            }

            animator.SetBool(runningParam, true);
            yield return new WaitForSeconds(step.duration);
            animator.SetBool(runningParam, false);
            yield return null; // let the Animator go back to idle
            yield break;
        }

        // TRIGGER ACTIONS: Attack, Jump, Beer, Hurt, Dead
        animator.SetTrigger(step.action.ToString());

        if (step.duration > 0f)
            yield return new WaitForSeconds(step.duration);   // fixed duration
        else
            yield return WaitForActionToEnd(step.action);     // natural end

        ReturnToIdle();
    }

    private IEnumerator WaitForActionToEnd(DinoAction action)
    {
        // Give the Animator a couple of frames to start the transition
        yield return null;
        yield return null;

        float timeout = Time.time + maxWaitForAnimation;

        while (Time.time < timeout)
        {
            AnimatorStateInfo info = animator.GetCurrentAnimatorStateInfo(Layer);

            if (action == DinoAction.Dead)
            {
                // Dead has no exit transition: wait until its clip finished once
                if (info.shortNameHash == deadHash && info.normalizedTime >= 1f)
                    yield break;
            }
            else
            {
                // The other actions exit by themselves back to idle
                if (info.shortNameHash == idleHash && !animator.IsInTransition(Layer))
                    yield break;
            }

            yield return null;
        }

        Debug.LogWarning($"[{name}] Timed out waiting for '{action}' to finish.", this);
    }

    private void ReturnToIdle()
    {
        ResetAllTriggers();

        AnimatorStateInfo info = animator.GetCurrentAnimatorStateInfo(Layer);
        if (info.shortNameHash != idleHash || animator.IsInTransition(Layer))
            animator.Play(idleHash, Layer, 0f);
    }

    private void ForceIdle()
    {
        animator.SetBool(runningParam, false);
        ResetAllTriggers();
        animator.Play(idleHash, Layer, 0f);
    }

    private void ResetAllTriggers()
    {
        foreach (string trigger in TriggerNames)
            animator.ResetTrigger(trigger);
    }
}