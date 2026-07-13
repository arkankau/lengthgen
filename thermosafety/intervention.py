from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from thermosafety.attention import NullAttractorConfig


@dataclass
class InterventionLog:
    records: list[dict[str, float]] = field(default_factory=list)

    def add(
        self,
        layer: int,
        risk: float,
        null_bias: float,
        beta: float,
        null_mass_by_head: Any,
        *,
        entropy_by_head: Any | None = None,
        psi_by_head: Any | None = None,
        spectral_gap_by_head: Any | None = None,
        selected_by_head: Any | None = None,
        mix_alpha: float = 1.0,
        phi_penalty_mean: float = 0.0,
        null_value_norm: float = 0.0,
    ) -> None:
        values = null_mass_by_head.detach().float().cpu().tolist()
        entropies = _optional_head_values(entropy_by_head, len(values), default=0.0)
        psis = _optional_head_values(psi_by_head, len(values), default=0.0)
        spectral_gaps = _optional_head_values(spectral_gap_by_head, len(values), default=0.0)
        selected = _optional_head_values(selected_by_head, len(values), default=1.0)
        for head, value in enumerate(values):
            self.records.append(
                {
                    "layer": float(layer),
                    "head": float(head),
                    "risk": float(risk),
                    "null_bias": float(null_bias),
                    "beta": float(beta),
                    "m_null": float(value),
                    "entropy": float(entropies[head]),
                    "psi": float(psis[head]),
                    "spectral_gap": float(spectral_gaps[head]),
                    "head_selected": float(selected[head]),
                    "mix_alpha": float(mix_alpha),
                    "phi_penalty_mean": float(phi_penalty_mean),
                    "null_value_norm": float(null_value_norm),
                }
            )

    def mean_null_mass(self) -> float:
        if not self.records:
            return 0.0
        return sum(record["m_null"] for record in self.records) / len(self.records)

    def mean(self, key: str) -> float:
        if not self.records:
            return 0.0
        return sum(record[key] for record in self.records) / len(self.records)


def _optional_head_values(values: Any | None, count: int, default: float) -> list[float]:
    if values is None:
        return [default] * count
    if hasattr(values, "detach"):
        return values.detach().float().cpu().tolist()
    return [float(value) for value in values]


def schedule_values(risk: float, config: NullAttractorConfig, torch: Any, device: Any, dtype: Any) -> tuple[Any, Any]:
    risk_tensor = torch.tensor(float(risk), device=device, dtype=dtype)
    gate = torch.sigmoid(torch.tensor(config.kappa, device=device, dtype=dtype) * (risk_tensor - config.risk_threshold))
    null_bias = torch.tensor(config.eta_null, device=device, dtype=dtype) * gate
    beta = torch.tensor(config.beta_base, device=device, dtype=dtype) + (
        torch.tensor(config.beta_collapse - config.beta_base, device=device, dtype=dtype) * gate
    )
    return null_bias, beta


def _safe_normalized_positive(values: Any, torch: Any) -> Any:
    positive = torch.relu(values)
    scale = positive.detach().amax(dim=-1, keepdim=True).clamp_min(1e-6)
    return positive / scale


def _unsafe_coupling(query: Any, key: Any, barrier: dict, layer_idx: int, gain: float, torch: Any) -> Any:
    """C_unsafe(i,j) = sigma(gain*cos(q_i,u_q)) * sigma(gain*cos(k_j,u_k)), per head.

    This is the free-energy barrier of the derivations (Sec. 5): it raises the energy of
    attention paths whose query AND key both align with a learned unsafe direction, leaving
    benign task couplings (either factor low) essentially untouched. Shapes: query/key are
    (batch, heads, seq, head_dim); u_q/u_k are (heads, head_dim); result matches base_logits.
    """
    if barrier is None or layer_idx not in barrier:
        return torch.zeros(*query.shape[:-1], key.shape[-2], device=query.device, dtype=query.dtype)
    u_q = barrier[layer_idx]["u_q"].to(device=query.device, dtype=query.dtype)  # (H, d)
    u_k = barrier[layer_idx]["u_k"].to(device=key.device, dtype=key.dtype)      # (H, d)
    q_n = torch.nn.functional.normalize(query, dim=-1)
    k_n = torch.nn.functional.normalize(key, dim=-1)
    cos_q = torch.einsum("bhid,hd->bhi", q_n, torch.nn.functional.normalize(u_q, dim=-1))
    cos_k = torch.einsum("bhjd,hd->bhj", k_n, torch.nn.functional.normalize(u_k, dim=-1))
    sig_q = torch.sigmoid(gain * cos_q).unsqueeze(-1)  # (b,h,i,1)
    sig_k = torch.sigmoid(gain * cos_k).unsqueeze(-2)  # (b,h,1,j)
    return sig_q * sig_k  # (b,h,i,j)


def phi_penalty(
    base_logits: Any,
    risk: float,
    config: NullAttractorConfig,
    torch: Any,
    *,
    query: Any | None = None,
    key: Any | None = None,
    barrier_bank: dict | None = None,
    layer_idx: int = -1,
) -> Any:
    """Return a risk-scaled Phi(Q,K,X) penalty over non-null couplings.

    `uniform` preserves the original behavior. `positive_logits`/`attention_sharpness` are crude
    proxies. `unsafe_coupling` is the theory-grounded free-energy barrier: it uses a learned
    unsafe direction in query/key space and only penalizes couplings where both the query and the
    key align with it, which is designed to suppress unsafe retrieval without collapsing benign
    task basins (unlike a global attractor).
    """
    if config.lambda_penalty <= 0.0:
        return torch.zeros_like(base_logits)
    if config.phi_mode == "uniform":
        phi = torch.ones_like(base_logits)
    elif config.phi_mode == "positive_logits":
        centered = base_logits - base_logits.mean(dim=-1, keepdim=True)
        phi = _safe_normalized_positive(centered, torch)
    elif config.phi_mode == "attention_sharpness":
        weights = torch.softmax(base_logits, dim=-1)
        phi = _safe_normalized_positive(weights - weights.mean(dim=-1, keepdim=True), torch)
    elif config.phi_mode == "unsafe_coupling":
        if query is None or key is None:
            raise ValueError("unsafe_coupling phi_mode requires query and key tensors")
        phi = _unsafe_coupling(query, key, barrier_bank, layer_idx, float(config.phi_unsafe_gain), torch)
    else:
        raise ValueError(f"unknown phi_mode: {config.phi_mode}")
    return float(config.lambda_penalty) * float(risk) * phi


def build_null_value(
    value: Any,
    config: NullAttractorConfig,
    torch: Any,
    *,
    layer_idx: int,
    risk: float,
    null_value_bank: dict[int, Any] | None = None,
) -> Any:
    """Create the appended null value in attention value space.

    `zero` is the original crude semantic sink. The contextual modes are
    refusal/safe-redirection proxies: they route collapse into an existing
    value-space direction instead of erasing the attention output. A learned
    refusal vector can later plug into this same seam.
    """
    mode = config.null_value_mode
    if mode == "zero":
        null_value = torch.zeros(*value.shape[:-2], 1, value.shape[-1], device=value.device, dtype=value.dtype)
    elif mode == "context_mean":
        null_value = value.mean(dim=-2, keepdim=True)
    elif mode == "first_token":
        null_value = value[..., :1, :]
    elif mode == "last_token":
        null_value = value[..., -1:, :]
    elif mode == "safe_redirection":
        prefix_len = min(4, value.shape[-2])
        prefix = value[..., :prefix_len, :].mean(dim=-2, keepdim=True)
        context = value.mean(dim=-2, keepdim=True)
        null_value = 0.5 * prefix + 0.5 * context
    elif mode == "calibrated_refusal":
        if null_value_bank is None or layer_idx not in null_value_bank:
            null_value = value.mean(dim=-2, keepdim=True)
        else:
            bank_value = null_value_bank[layer_idx]
            calibrated = bank_value["refusal"] if isinstance(bank_value, dict) else bank_value
            calibrated = calibrated.to(device=value.device, dtype=value.dtype)
            null_value = calibrated.view(1, calibrated.shape[0], 1, calibrated.shape[1]).expand(
                value.shape[0],
                -1,
                -1,
                -1,
            )
    elif mode in {"semantic_refusal", "semantic_redirection"}:
        if null_value_bank is None or layer_idx not in null_value_bank or not isinstance(null_value_bank[layer_idx], dict):
            null_value = value.mean(dim=-2, keepdim=True)
        else:
            bank = null_value_bank[layer_idx]
            context = value.mean(dim=-2, keepdim=True)
            refusal = bank["refusal"].to(device=value.device, dtype=value.dtype)
            unsafe = bank["unsafe"].to(device=value.device, dtype=value.dtype)
            direction = refusal - unsafe
            if mode == "semantic_redirection":
                redirect = bank.get("redirect", refusal).to(device=value.device, dtype=value.dtype)
                hard_gate = torch.sigmoid(
                    torch.tensor(config.kappa, device=value.device, dtype=value.dtype)
                    * (torch.tensor(float(risk), device=value.device, dtype=value.dtype) - float(config.redirect_risk_threshold))
                )
                target = ((1.0 - hard_gate) * redirect) + (hard_gate * refusal)
                semantic = target + float(config.semantic_attractor_strength) * direction
            else:
                semantic = refusal + float(config.semantic_attractor_strength) * direction
            null_value = (0.5 * context) + (
                0.5
                * semantic.view(1, semantic.shape[0], 1, semantic.shape[1]).expand(
                    value.shape[0],
                    -1,
                    -1,
                    -1,
                )
            )
    else:
        raise ValueError(f"unknown null_value_mode: {mode}")
    if config.null_value_scale != 0.0:
        null_value = null_value + float(config.null_value_scale)
    return null_value


def attention_diagnostics(attn_weights: Any, torch: Any) -> tuple[Any, Any, Any]:
    clipped = attn_weights.clamp_min(1e-12)
    entropy = -(clipped * clipped.log()).sum(dim=-1).mean(dim=(0, 2))
    null_mass = attn_weights[..., -1]
    max_non_null = attn_weights[..., :-1].amax(dim=-1)
    psi = (null_mass - max_non_null).mean(dim=(0, 2))
    spectral_gaps = []
    real_kernel = attn_weights[..., :-1].detach().float()
    for head in range(real_kernel.shape[1]):
        kernel = real_kernel[:, head].mean(dim=0)
        if kernel.shape[0] != kernel.shape[1]:
            masses = kernel.mean(dim=0)
            sorted_masses = torch.sort(masses, descending=True).values
            second = sorted_masses[1] if sorted_masses.numel() > 1 else torch.tensor(0.0, device=attn_weights.device)
            spectral_gaps.append((1.0 - second).clamp_min(0.0).to(attn_weights.dtype))
            continue
        row_sums = kernel.sum(dim=-1, keepdim=True)
        normalized = torch.where(row_sums > 0, kernel / row_sums.clamp_min(1e-12), torch.zeros_like(kernel))
        if normalized.shape[0] <= 1:
            spectral_gaps.append(torch.tensor(1.0, device=attn_weights.device, dtype=attn_weights.dtype))
            continue
        eigvals = torch.linalg.eigvals(normalized).abs()
        sorted_vals = torch.sort(eigvals, descending=True).values
        lambda_2 = sorted_vals[1] if sorted_vals.numel() > 1 else torch.tensor(0.0, device=attn_weights.device)
        spectral_gaps.append((1.0 - lambda_2.real).clamp_min(0.0).to(attn_weights.dtype))
    return entropy, psi, torch.stack(spectral_gaps)


def _repeat_kv(hidden_states: Any, n_rep: int, torch: Any) -> Any:
    """Expand grouped-query-attention key/value heads to match query head count.

    Equivalent to `torch.repeat_interleave(x, dim=1, repeats=n_rep)`. GPT-2-family
    models have `n_rep == 1` (a no-op); GQA models such as Qwen2 have `n_rep > 1`
    because they share each key/value head across several query heads.
    """
    if n_rep == 1:
        return hidden_states
    batch, num_kv_heads, seq_len, head_dim = hidden_states.shape
    expanded = hidden_states[:, :, None, :, :].expand(batch, num_kv_heads, n_rep, seq_len, head_dim)
    return expanded.reshape(batch, num_kv_heads * n_rep, seq_len, head_dim)


def _generic_eager_attention_forward(
    module: Any,
    query: Any,
    key: Any,
    value: Any,
    attention_mask: Any,
    torch: Any,
    *,
    scaling: float,
    dropout: float = 0.0,
    **kwargs: Any,
) -> tuple[Any, Any]:
    """Architecture-agnostic eager attention fallback, with GQA key/value expansion."""
    from torch import nn

    n_rep = query.shape[1] // key.shape[1]
    key_states = _repeat_kv(key, n_rep, torch)
    value_states = _repeat_kv(value, n_rep, torch)

    attn_weights = torch.matmul(query, key_states.transpose(-1, -2)) * scaling
    if attention_mask is not None:
        attn_weights = attn_weights + attention_mask
    attn_weights = nn.functional.softmax(attn_weights, dim=-1, dtype=torch.float32).to(query.dtype)
    attn_weights = nn.functional.dropout(attn_weights, p=dropout, training=module.training)
    attn_output = torch.matmul(attn_weights, value_states)
    attn_output = attn_output.transpose(1, 2).contiguous()
    return attn_output, attn_weights


def build_null_logits(base_logits: Any, attention_mask: Any, config: NullAttractorConfig, torch: Any) -> Any:
    """Compute the appended null slot's pre-bias attention logit.

    `zero` hardcodes the logit to `config.null_key_scale` (default 0.0) regardless of the
    real query-key logits at this layer. This makes the null slot's baseline competitiveness
    an artifact of each layer's absolute logit scale rather than a risk-conditioned quantity
    (confirmed empirically: at some layers a flat-zero logit is far more attractive than real
    keys even with risk-gating fully disabled, at others far less).

    `mean_logit` instead sets the null logit to the mean of the real (causally valid) logits
    at this query position, so the null slot starts as an "average-strength" attractor,
    self-normalized to each layer's own scale. The risk-gated bias added on top then
    represents the risk-driven excess over a typical real key, which is the intended
    thermodynamic reading (a controlled perturbation relative to the local energy landscape,
    not an absolute offset).
    """
    if config.null_key_mode == "zero":
        return torch.zeros(*base_logits.shape[:-1], 1, device=base_logits.device, dtype=base_logits.dtype) + config.null_key_scale
    if config.null_key_mode == "mean_logit":
        if attention_mask is not None:
            valid = attention_mask == 0
            masked_logits = torch.where(valid, base_logits, torch.zeros_like(base_logits))
            counts = valid.sum(dim=-1, keepdim=True).clamp_min(1).to(base_logits.dtype)
            mean_logits = masked_logits.sum(dim=-1, keepdim=True) / counts
        else:
            mean_logits = base_logits.mean(dim=-1, keepdim=True)
        return mean_logits + config.null_key_scale
    raise ValueError(f"unknown null_key_mode: {config.null_key_mode}")


def null_attractor_attention_forward(
    module: Any,
    query: Any,
    key: Any,
    value: Any,
    attention_mask: Any,
    *,
    risk: float,
    config: NullAttractorConfig,
    log: InterventionLog | None = None,
    selected_layers: set[int] | None = None,
    selected_heads: set[int] | None = None,
    null_value_bank: dict[int, Any] | None = None,
    barrier_bank: dict[int, Any] | None = None,
    scaling: float | None = None,
    dropout: float = 0.0,
    **kwargs: Any,
) -> tuple[Any, Any]:
    """Architecture-agnostic eager attention with an appended configurable null basin.

    This is an experimental in-layer intervention scaffold. The null value is a
    configurable value-space vector, so attention mass assigned to the null slot
    can drain, soften, or redirect ordinary attention while preserving expected
    tensor shapes. Key/value heads are expanded to match query heads first, so
    grouped-query-attention architectures (e.g. Qwen2) behave the same as
    multi-head architectures (e.g. GPT-2, where the expansion is a no-op).
    """
    import torch
    from torch import nn

    if scaling is None:
        scaling = query.size(-1) ** -0.5

    layer_idx = int(getattr(module, "layer_idx", -1))
    if selected_layers is not None and layer_idx not in selected_layers:
        return _generic_eager_attention_forward(
            module,
            query,
            key,
            value,
            attention_mask,
            torch,
            scaling=scaling,
            dropout=dropout,
            **kwargs,
        )

    n_rep = query.shape[1] // key.shape[1]
    key = _repeat_kv(key, n_rep, torch)
    value = _repeat_kv(value, n_rep, torch)

    base_logits = torch.matmul(query, key.transpose(-1, -2)) * scaling
    null_logits = build_null_logits(base_logits, attention_mask, config, torch)
    attn_logits = torch.cat([base_logits, null_logits], dim=-1)

    if attention_mask is not None:
        null_mask = torch.zeros(*attention_mask.shape[:-1], 1, device=attention_mask.device, dtype=attention_mask.dtype)
        attention_mask = torch.cat([attention_mask, null_mask], dim=-1)
        attn_logits = attn_logits + attention_mask

    null_bias, beta = schedule_values(risk, config, torch, attn_logits.device, attn_logits.dtype)
    penalty = torch.zeros_like(attn_logits)
    real_penalty = phi_penalty(
        base_logits, risk, config, torch,
        query=query, key=key, barrier_bank=barrier_bank, layer_idx=layer_idx,
    )
    penalty[..., :-1] = real_penalty
    bias = torch.zeros_like(attn_logits)
    bias[..., -1] = null_bias
    intervened_logits = beta * (attn_logits - penalty + bias)

    if selected_heads is not None:
        head_mask = torch.zeros(attn_logits.shape[1], device=attn_logits.device, dtype=torch.bool)
        for head in selected_heads:
            if 0 <= int(head) < attn_logits.shape[1]:
                head_mask[int(head)] = True
        null_block = torch.zeros_like(attn_logits)
        null_block[..., -1] = torch.finfo(attn_logits.dtype).min
        baseline_ext_logits = attn_logits + null_block
        intervened_logits = torch.where(head_mask.view(1, -1, 1, 1), intervened_logits, baseline_ext_logits)
        selected_by_head = head_mask.to(attn_logits.dtype)
    else:
        selected_by_head = torch.ones(attn_logits.shape[1], device=attn_logits.device, dtype=attn_logits.dtype)

    attn_weights = nn.functional.softmax(intervened_logits, dim=-1).type(value.dtype)
    mix_alpha = max(0.0, min(1.0, float(config.intervention_mix)))
    if mix_alpha < 1.0:
        null_block = torch.zeros_like(attn_logits)
        null_block[..., -1] = torch.finfo(attn_logits.dtype).min
        baseline_weights = nn.functional.softmax(attn_logits + null_block, dim=-1).type(value.dtype)
        attn_weights = (mix_alpha * attn_weights) + ((1.0 - mix_alpha) * baseline_weights)
    attn_weights = nn.functional.dropout(attn_weights, p=dropout, training=module.training)
    null_mass_by_head = attn_weights[..., -1].mean(dim=(0, 2))
    entropy_by_head, psi_by_head, spectral_gap_by_head = attention_diagnostics(attn_weights, torch)
    null_value = build_null_value(value, config, torch, layer_idx=layer_idx, risk=risk, null_value_bank=null_value_bank)
    null_value_norm = float(null_value.detach().float().norm(dim=-1).mean().cpu())
    if log is not None:
        log.add(
            layer_idx,
            risk,
            float(null_bias.detach().cpu()),
            float(beta.detach().cpu()),
            null_mass_by_head,
            entropy_by_head=entropy_by_head,
            psi_by_head=psi_by_head,
            spectral_gap_by_head=spectral_gap_by_head,
            selected_by_head=selected_by_head,
            mix_alpha=mix_alpha,
            phi_penalty_mean=float(real_penalty.detach().float().mean().cpu()),
            null_value_norm=null_value_norm,
        )

    value_ext = torch.cat([value, null_value], dim=-2)
    attn_output = torch.matmul(attn_weights, value_ext)
    attn_output = attn_output.transpose(1, 2)
    return attn_output, attn_weights[..., :-1]


@contextmanager
def patch_gpt2_attention(
    model: Any,
    *,
    risk: float,
    config: NullAttractorConfig | None = None,
    selected_layers: set[int] | None = None,
    selected_heads: set[int] | None = None,
    null_value_bank: dict[int, Any] | None = None,
    barrier_bank: dict[int, Any] | None = None,
) -> Iterator[InterventionLog]:
    """Temporarily register a GPT-2 attention implementation with null bias."""
    from transformers.models.gpt2 import modeling_gpt2

    cfg = config or NullAttractorConfig()
    log = InterventionLog()
    key = "thermosafety_null_attractor"
    original_impl = getattr(model.config, "_attn_implementation", "eager")

    def attention_impl(module: Any, query: Any, key_tensor: Any, value: Any, attention_mask: Any, **kwargs: Any) -> tuple[Any, Any]:
        return null_attractor_attention_forward(
            module,
            query,
            key_tensor,
            value,
            attention_mask,
            risk=risk,
            config=cfg,
            log=log,
            selected_layers=selected_layers,
            selected_heads=selected_heads,
            null_value_bank=null_value_bank,
            barrier_bank=barrier_bank,
            **kwargs,
        )

    modeling_gpt2.ALL_ATTENTION_FUNCTIONS.register(key, attention_impl)
    model.config._attn_implementation = key
    try:
        yield log
    finally:
        model.config._attn_implementation = original_impl
        try:
            modeling_gpt2.ALL_ATTENTION_FUNCTIONS.pop(key)
        except KeyError:
            pass


def calibrate_refusal_value_bank(
    model: Any,
    tokenizer: Any,
    *,
    anchor_text: str,
    device: str,
    selected_layers: set[int] | None = None,
) -> dict[int, Any]:
    """Capture per-layer/head value-space vectors from a safe-refusal anchor.

    This gives the null slot a calibrated direction in the model's own value
    space. It is not a learned refusal manifold yet, but it is materially closer
    to the intended thermodynamic attractor than a zero sink.
    """
    import torch
    from transformers.models.gpt2 import modeling_gpt2

    captures: dict[int, list[Any]] = {}
    key = "thermosafety_value_capture"
    original_impl = getattr(model.config, "_attn_implementation", "eager")

    def attention_impl(module: Any, query: Any, key_tensor: Any, value: Any, attention_mask: Any, **kwargs: Any) -> tuple[Any, Any]:
        layer_idx = int(getattr(module, "layer_idx", -1))
        n_rep = query.shape[1] // value.shape[1]
        expanded_value = _repeat_kv(value, n_rep, torch)
        if selected_layers is None or layer_idx in selected_layers:
            captures.setdefault(layer_idx, []).append(expanded_value.detach().float().mean(dim=(0, 2)).cpu())
        scaling = kwargs.pop("scaling", None)
        if scaling is None:
            scaling = query.size(-1) ** -0.5
        dropout = kwargs.pop("dropout", 0.0)
        return _generic_eager_attention_forward(
            module, query, key_tensor, value, attention_mask, torch, scaling=scaling, dropout=dropout, **kwargs
        )

    modeling_gpt2.ALL_ATTENTION_FUNCTIONS.register(key, attention_impl)
    model.config._attn_implementation = key
    try:
        encoded = tokenizer(anchor_text, return_tensors="pt").to(device)
        with torch.no_grad():
            model(**encoded)
    finally:
        model.config._attn_implementation = original_impl
        try:
            modeling_gpt2.ALL_ATTENTION_FUNCTIONS.pop(key)
        except KeyError:
            pass

    return {layer: torch.stack(values).mean(dim=0) for layer, values in captures.items()}


def calibrate_semantic_value_bank(
    model: Any,
    tokenizer: Any,
    *,
    refusal_anchor: str,
    unsafe_anchor: str,
    redirect_anchor: str,
    device: str,
    selected_layers: set[int] | None = None,
) -> dict[int, dict[str, Any]]:
    """Capture refusal, unsafe, and redirection value-space anchors.

    This turns the key paper move into a testable attractor: instead of sending
    attention into a blank sink, the appended slot writes a direction estimated
    from refusal-minus-unsafe value states, optionally blended with a safe
    redirection anchor.
    """
    refusal_bank = calibrate_refusal_value_bank(
        model,
        tokenizer,
        anchor_text=refusal_anchor,
        device=device,
        selected_layers=selected_layers,
    )
    unsafe_bank = calibrate_refusal_value_bank(
        model,
        tokenizer,
        anchor_text=unsafe_anchor,
        device=device,
        selected_layers=selected_layers,
    )
    redirect_bank = calibrate_refusal_value_bank(
        model,
        tokenizer,
        anchor_text=redirect_anchor,
        device=device,
        selected_layers=selected_layers,
    )
    layers = set(refusal_bank) & set(unsafe_bank)
    return {
        layer: {
            "refusal": refusal_bank[layer],
            "unsafe": unsafe_bank[layer],
            "redirect": redirect_bank.get(layer, refusal_bank[layer]),
        }
        for layer in layers
    }


def _capture_qk_means(model: Any, tokenizer: Any, anchor_text: str, device: str) -> dict[int, dict[str, Any]]:
    """Per-layer/head mean query and (repeated) key vectors for one anchor prompt."""
    import torch
    from transformers.models.gpt2 import modeling_gpt2

    captures: dict[int, dict[str, Any]] = {}
    key = "thermosafety_qk_capture"
    original_impl = getattr(model.config, "_attn_implementation", "eager")

    def attention_impl(module: Any, query: Any, key_tensor: Any, value: Any, attention_mask: Any, **kwargs: Any) -> tuple[Any, Any]:
        layer_idx = int(getattr(module, "layer_idx", -1))
        n_rep = query.shape[1] // key_tensor.shape[1]
        exp_key = _repeat_kv(key_tensor, n_rep, torch)
        captures[layer_idx] = {
            "q": query.detach().float().mean(dim=(0, 2)).cpu(),      # (H, d)
            "k": exp_key.detach().float().mean(dim=(0, 2)).cpu(),    # (H, d)
        }
        scaling = kwargs.pop("scaling", None)
        if scaling is None:
            scaling = query.size(-1) ** -0.5
        dropout = kwargs.pop("dropout", 0.0)
        return _generic_eager_attention_forward(
            module, query, key_tensor, value, attention_mask, torch, scaling=scaling, dropout=dropout, **kwargs
        )

    modeling_gpt2.ALL_ATTENTION_FUNCTIONS.register(key, attention_impl)
    model.config._attn_implementation = key
    try:
        encoded = tokenizer(anchor_text, return_tensors="pt").to(device)
        with torch.no_grad():
            model(**encoded)
    finally:
        model.config._attn_implementation = original_impl
        try:
            modeling_gpt2.ALL_ATTENTION_FUNCTIONS.pop(key)
        except KeyError:
            pass
    return captures


def calibrate_qk_unsafe_bank(
    model: Any,
    tokenizer: Any,
    *,
    refusal_anchor: str,
    unsafe_anchor: str,
    device: str,
) -> dict[int, dict[str, Any]]:
    """Per-layer unsafe directions in query/key space: u = normalize(mean_unsafe - mean_refusal).

    These feed the free-energy barrier (phi_mode='unsafe_coupling'). Unlike the value-space
    semantic anchors, these live in the head's query/key projection, which is where the barrier
    must act to reshape attention logits.
    """
    import torch

    refusal = _capture_qk_means(model, tokenizer, refusal_anchor, device)
    unsafe = _capture_qk_means(model, tokenizer, unsafe_anchor, device)
    bank: dict[int, dict[str, Any]] = {}
    for layer in set(refusal) & set(unsafe):
        u_q = unsafe[layer]["q"] - refusal[layer]["q"]
        u_k = unsafe[layer]["k"] - refusal[layer]["k"]
        bank[layer] = {
            "u_q": torch.nn.functional.normalize(u_q, dim=-1),
            "u_k": torch.nn.functional.normalize(u_k, dim=-1),
        }
    return bank
