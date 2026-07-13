from __future__ import annotations

from dataclasses import dataclass

from thermosafety.embeddings import tokenize


@dataclass(frozen=True)
class RiskBreakdown:
    score: float
    intent: float
    obfuscation: float
    hierarchy_conflict: float
    benign_context: float


UNSAFE_TERMS = {
    "jailbreak",
    "bypass",
    "ignore",
    "override",
    "malware",
    "exploit",
    "payload",
    "steal",
    "credential",
    "weapon",
    "harm",
    "illegal",
    "exfiltrate",
}

HIERARCHY_TERMS = {"ignore", "developer", "system", "policy", "rules", "override"}
BENIGN_CONTEXT = {
    "defense",
    "detect",
    "prevention",
    "safety",
    "research",
    "policy",
    "legal",
    "educational",
    "high-level",
    "overview",
}


def score_risk(text: str) -> RiskBreakdown:
    """Heuristic trajectory-risk proxy for the toy experiment.

    This is deliberately not framed as a final defense. It supplies a rough
    control variable for testing whether null mass behaves like an order
    parameter under changing risk.
    """
    tokens = tokenize(text)
    token_set = set(tokens)
    if not tokens:
        return RiskBreakdown(0.0, 0.0, 0.0, 0.0, 0.0)

    unsafe_hits = sum(1 for t in tokens if t in UNSAFE_TERMS)
    hierarchy_hits = sum(1 for t in tokens if t in HIERARCHY_TERMS)
    benign_hits = sum(1 for t in tokens if t in BENIGN_CONTEXT)
    unusual = sum(1 for t in tokens if any(ch.isdigit() for ch in t) or len(t) > 18)

    intent = min(1.0, unsafe_hits / 3.0)
    hierarchy_conflict = min(1.0, hierarchy_hits / 3.0)
    obfuscation = min(1.0, unusual / max(1, len(tokens) // 8 + 1))
    benign_context = min(1.0, benign_hits / 4.0)

    imperative = 0.12 if token_set & {"give", "write", "create", "provide", "show"} else 0.0
    score = (
        0.08
        + 0.46 * intent
        + 0.22 * hierarchy_conflict
        + 0.16 * obfuscation
        + imperative
        - 0.22 * benign_context
    )
    return RiskBreakdown(
        score=max(0.0, min(1.0, score)),
        intent=intent,
        obfuscation=obfuscation,
        hierarchy_conflict=hierarchy_conflict,
        benign_context=benign_context,
    )
