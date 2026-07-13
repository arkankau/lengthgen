# Multi-Perspective Research Method

**Source:** Adapted from an X post by Nav Toor (@heynavtoor), which itself draws on Stanford's STORM system (Synthesis of Topic Outlines through Retrieval and Multi-perspective Question Asking), published at NAACL 2024 by the Stanford OVAL Lab. Live demo: storm.genie.stanford.edu. Code: github.com/stanford-oval/storm (MIT license).

## Why this exists

A single research query tends to surface the consensus view and misses what a domain expert, a critic, or someone tracking incentives would actually flag. STORM's core finding was that generating research from multiple simulated viewpoints and then reconciling them produces meaningfully better-organized, broader-coverage output than a single pass. This directive turns that idea into a 4-stage workflow Claude Code can run against any research topic.

## Workflow

Run these four stages in order, feeding each stage's output into the next.

### Stage 1 — Multi-perspective scan
For the target topic, generate five distinct viewpoints:
- **Practitioner** — someone who works with this hands-on; what do they know that outsiders miss?
- **Researcher/academic** — what does the peer-reviewed or primary-source evidence actually say, especially where it cuts against popular belief?
- **Skeptic** — the strongest good-faith case against the mainstream take, and what evidence gets glossed over.
- **Incentives analyst** — who benefits financially or politically from the dominant narrative, and how that shapes what gets published or repeated.
- **Historian** — analogous situations from the past, and what happened when they played out.

For each: a two-sentence core position, the strongest supporting evidence, and the one insight that viewpoint uniquely contributes.

### Stage 2 — Contradiction map
Compare the five viewpoints and identify:
- Direct conflicts between perspectives, stated as specific clashing claims
- Which side has stronger evidence, and why
- The single question that would resolve the biggest disagreement
- Points of universal agreement (a good signal of reliability)
- Anything none of the five perspectives addressed (often the real gap)

### Stage 3 — Synthesis briefing
Combine everything into:
1. A one-paragraph executive summary
2. Five key findings, ranked by reliability, each noting which perspectives support/challenge it
3. One non-obvious connection that only appears when viewing all five perspectives together
4. A concrete, specific action recommendation
5. The open question that would most change the picture if answered

### Stage 4 — Self peer-review
Grade the synthesis before trusting it:
- Confidence score (1–10) per key finding, with reasoning
- Weakest claim, and what would be needed to verify it
- Whether one perspective dominated the synthesis (bias check)
- Whether a sixth angle is missing that would change the conclusions
- An overall grade and what to fix

## Usage in Claude Code

Drop this file into a project (e.g. `docs/multi-perspective-research.md`) and reference it in a prompt:

> "Use the workflow in `docs/multi-perspective-research.md` to research [topic]. Run all four stages and give me the final synthesis plus the peer-review grade."

Good fits: technical due diligence on a library/vendor choice, evaluating a research direction before committing time, prepping for a decision with real tradeoffs, or building out a `CLAUDE.md` research routine that gets reused across projects.

## Caveat worth keeping in mind

This is a prompting pattern, not literal Stanford STORM — no retrieval pipeline, no citations pulled from real sources unless you separately have Claude search the web. Treat the output as a structured reasoning exercise that surfaces angles and tensions, not as sourced fact; verify anything load-bearing before acting on it.
