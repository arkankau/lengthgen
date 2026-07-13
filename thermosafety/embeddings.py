from __future__ import annotations

import hashlib
import re

import numpy as np

TOKEN_RE = re.compile(r"[a-zA-Z0-9_'-]+")

UNSAFE_ANCHORS = {
    "bypass",
    "jailbreak",
    "ignore",
    "override",
    "malware",
    "exploit",
    "payload",
    "steal",
    "weapon",
    "harm",
}

BENIGN_ANCHORS = {
    "explain",
    "summarize",
    "compare",
    "policy",
    "safety",
    "research",
    "defense",
    "legal",
    "medical",
    "education",
}


def tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text)]


def token_vector(token: str, dim: int = 32) -> np.ndarray:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], "little", signed=False)
    rng = np.random.default_rng(seed)
    vec = rng.normal(0.0, 1.0, size=dim)

    if token in UNSAFE_ANCHORS:
        vec[0] += 3.0
        vec[1] -= 1.5
    if token in BENIGN_ANCHORS:
        vec[0] -= 1.0
        vec[2] += 2.0

    norm = np.linalg.norm(vec)
    return vec / norm if norm else vec


def embed_prompt(text: str, dim: int = 32) -> np.ndarray:
    tokens = tokenize(text)
    if not tokens:
        tokens = ["empty"]
    return np.vstack([token_vector(token, dim=dim) for token in tokens])
