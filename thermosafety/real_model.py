from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


class OptionalDependencyError(RuntimeError):
    pass


@dataclass(frozen=True)
class RealModelTrace:
    prompt: str
    tokens: list[str]
    hidden_states: list[np.ndarray]
    attentions: list[np.ndarray]


def _load_hf_modules() -> tuple[Any, Any, Any]:
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise OptionalDependencyError(
            "Phase 2 real-model diagnostics require optional dependencies: "
            "torch and transformers."
        ) from exc
    return torch, AutoModelForCausalLM, AutoTokenizer


def load_model(model_name: str, device: str = "cpu", local_files_only: bool = False) -> tuple[Any, Any, Any]:
    torch, auto_model, auto_tokenizer = _load_hf_modules()
    tokenizer = auto_tokenizer.from_pretrained(model_name, local_files_only=local_files_only)
    model = auto_model.from_pretrained(model_name, local_files_only=local_files_only)
    model.to(device)
    model.eval()
    return torch, tokenizer, model


def extract_trace(
    prompt: str,
    model_name: str = "sshleifer/tiny-gpt2",
    max_length: int = 128,
    device: str = "cpu",
    local_files_only: bool = False,
) -> RealModelTrace:
    """Extract hidden states and native attentions from a small HF causal LM."""
    torch, tokenizer, model = load_model(
        model_name=model_name,
        device=device,
        local_files_only=local_files_only,
    )
    return extract_trace_from_loaded(
        prompt=prompt,
        torch=torch,
        tokenizer=tokenizer,
        model=model,
        max_length=max_length,
        device=device,
    )


def extract_trace_from_loaded(
    prompt: str,
    torch: Any,
    tokenizer: Any,
    model: Any,
    max_length: int = 128,
    device: str = "cpu",
) -> RealModelTrace:
    """Extract a trace using an already loaded tokenizer/model pair."""
    encoded = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_length)
    encoded = {key: value.to(device) for key, value in encoded.items()}

    with torch.no_grad():
        outputs = model(**encoded, output_hidden_states=True, output_attentions=True)

    input_ids = encoded["input_ids"][0].detach().cpu().tolist()
    tokens = tokenizer.convert_ids_to_tokens(input_ids)
    hidden_states = [
        layer[0].detach().cpu().float().numpy()
        for layer in outputs.hidden_states
    ]
    attentions = [
        layer[0].detach().cpu().float().numpy()
        for layer in outputs.attentions or []
    ]
    return RealModelTrace(
        prompt=prompt,
        tokens=tokens,
        hidden_states=hidden_states,
        attentions=attentions,
    )


def hidden_state_features(trace: RealModelTrace) -> dict[str, float]:
    """Small, interpretable trajectory features for Phase 2 diagnostics."""
    final = trace.hidden_states[-1]
    first_token = final[0]
    last_token = final[-1]
    drift = float(np.linalg.norm(last_token - first_token))
    token_norm = float(np.mean(np.linalg.norm(final, axis=-1)))

    layer_centroids = np.vstack([layer.mean(axis=0) for layer in trace.hidden_states])
    layer_steps = np.diff(layer_centroids, axis=0)
    layer_drift = float(np.sum(np.linalg.norm(layer_steps, axis=-1))) if len(layer_steps) else 0.0

    attention_entropy = 0.0
    attention_peak = 0.0
    if trace.attentions:
        entropies = []
        peaks = []
        for layer in trace.attentions:
            clipped = np.clip(layer, 1e-12, 1.0)
            entropies.append(float(np.mean(-np.sum(clipped * np.log(clipped), axis=-1))))
            peaks.append(float(np.mean(np.max(layer, axis=-1))))
        attention_entropy = float(np.mean(entropies))
        attention_peak = float(np.mean(peaks))

    return {
        "hidden_token_drift": drift,
        "hidden_norm": token_norm,
        "layer_path_length": layer_drift,
        "native_attention_entropy": attention_entropy,
        "native_attention_peak": attention_peak,
    }
