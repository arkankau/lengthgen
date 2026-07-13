# Loop Engineering

**Source:** Adapted from an X/blog post on "Loop Engineering" (the Karpathy Method), covering Andrej Karpathy's AutoResearch repo (released March 2026) and the follow-up "Bilevel Autoresearch" paper.

## The core idea

A prompt is a single request-response exchange — you stay in the loop, deciding what happens next after every turn. A **loop** is different: you define a goal and a way to check progress, and the agent keeps planning, acting, and re-checking against that goal on its own until it either succeeds or hits a limit, without you prompting each step.

Three things make a loop actually work, as opposed to just an agent talking to itself:

- **A verifier** — an automated pass/fail signal (a test suite, a type checker, a build, a metric). Without this, the agent just grades its own homework and convinces itself it's done.
- **State** — a persistent record (a file, a log) of what's been tried and what failed, so each run picks up where the last one left off instead of re-deriving everything from zero.
- **A stop condition** — either the goal is met, or a hard cap ("stop after N attempts and report") kicks in. No exit condition means it runs until it succeeds, breaks, or exhausts your budget.

## Should you actually build one?

A loop is only worth the setup cost when all four of these hold:

1. The task recurs regularly (at least weekly) — a one-off is better served by a single good prompt.
2. Verification is automated — something that can fail the work without a human reviewing every diff.
3. Your token budget can absorb wasted cycles — loops re-read context and retry, which costs tokens whether or not a given run ships anything.
4. The agent has real tools — it can run what it writes and observe the actual result, not just reason about it abstractly.

If you're on a constrained plan or the task doesn't repeat, skip the heavy version — a simple manual loop (see below) captures most of the benefit without the overhead.

## The reference implementation: Karpathy's AutoResearch

A minimal three-file setup:
- A training/work script the agent is allowed to modify
- An evaluator the agent is *not* allowed to touch (otherwise it just makes the test easier instead of improving the work)
- An instructions file describing what to explore and what constraints to respect

The loop cycle: read the current state → propose a change → run it → check whether the result improved → keep the change or roll it back → repeat. Run overnight, wake up to a log of every experiment tried.

In practice this surfaced a meaningful number of optimizations a careful human had missed over years of manual tuning — not from being smarter, but from not getting tired after the first dozen experiments the way a person does.

## Five building blocks of a working loop

1. **Automation** — the trigger that fires the loop (a schedule, an event, a standing goal condition). Without this it's a script you ran once, not a loop.
2. **A skill/knowledge file** — project conventions, build steps, past gotchas, written once and read by every run, so context compounds instead of resetting each cycle.
3. **Sub-agents (maker vs. checker)** — the agent that wrote the code is a bad judge of its own work. A second agent with stricter, different instructions reviewing it catches what the first one talked itself into.
4. **Connectors** — access to the real environment (issue tracker, PRs, chat), so the loop can ship and report, not just describe a fix.
5. **A verifier** — the actual gate described above. Everything else is plumbing around this piece.

## The next layer: loops on loops (Bilevel Autoresearch)

A follow-up approach runs two nested loops:
- **Inner loop** — does the standard propose/train/evaluate/keep-or-discard cycle
- **Outer loop** — watches the inner loop, notices when it keeps falling back on the same unproductive search patterns, and rewrites how the inner loop searches

Reported result on a pretraining benchmark: roughly a 5x improvement over the single-loop version — using the *same* underlying model at both levels. The gain came from breaking the model's default habits/priors, not from a smarter model.

## A loop you can run right now, no infrastructure

Paste something like this into any LLM to get the core mechanic without building any tooling:

```
Work in a loop until the task meets the bar.

TASK: [what you want produced]

SUCCESS CRITERIA (be strict):
- [criterion 1]
- [criterion 2]
- [criterion 3]

Each turn:
1. State the next single step.
2. Do or improve the work.
3. Score the result 1-10 against each criterion, honestly,
   and name what's still weak.
4. If every score is 8+, stop and mark it final. Otherwise,
   fix the weakest criterion first and go again.

Don't ask clarifying questions — make a reasonable assumption
and continue.
```

This has no schedule and no persistent state across sessions, but it demonstrates the plan → do → verify → decide cycle that the full version automates.

## What loops don't fix

Two failure modes get worse, not better, as loops improve:

- **Comprehension debt** — the faster a loop ships work you didn't personally write, the wider the gap between what's in your codebase and what you actually understand. That gap compounds until someone has to debug a system nobody on the team has read.
- **Cognitive surrender** — it's easy to stop forming an opinion on output once a loop is running smoothly and just accept whatever comes back. The same tool sharpens your judgment or replaces it, depending on whether you're using it to move faster on work you understand or to avoid understanding the work at all.

## Usage in Claude Code

Save as `docs/loop-engineering.md` and reference it when setting up an actual automated loop:

> "Set up a loop per `docs/loop-engineering.md` for [recurring task]: verifier is [test/build/metric], state file at [path], stop after [N] attempts or when [condition]."

Pairs naturally with the multi-perspective research method file — research a decision first, then loop the execution once you've committed to a direction.
