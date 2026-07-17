from __future__ import annotations

import sys
from pathlib import Path

import torch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "colab"))
import length_gen_colab as lengthgen  # noqa: E402


def _attention():
    torch.manual_seed(7)
    attention = torch.rand(2, 3, 7, 7)
    return attention / attention.sum(dim=-1, keepdim=True)


def _apply(mode):
    attention = _attention()
    answer_queries = torch.tensor([5, 6])
    targets = torch.tensor([2, 3])
    lengthgen.PATCH = {"mode": mode, "diagnostics": {}}
    patched = lengthgen._apply_attn_patch(attention, answer_queries, targets)
    diagnostics = dict(lengthgen.PATCH["diagnostics"])
    lengthgen.PATCH = None
    return attention, patched, answer_queries, targets, diagnostics


def test_source_extrema_are_assigned_without_changing_spectrum():
    for mode, reduce in (("source_max", torch.max), ("source_min", torch.min)):
        before, after, queries, targets, diagnostics = _apply(mode)
        assert torch.equal(before.sort(dim=-1).values, after.sort(dim=-1).values)
        assert diagnostics["sorted"] == 0.0
        for batch, (query, target) in enumerate(zip(queries, targets)):
            original_rows = before[batch, :, query, : query + 1]
            expected = reduce(original_rows, dim=-1).values
            assert torch.equal(after[batch, :, query, target], expected)


def test_distractor_control_preserves_source_mass_and_spectrum():
    before, after, queries, targets, diagnostics = _apply("distractor_control")
    assert torch.equal(before.sort(dim=-1).values, after.sort(dim=-1).values)
    assert diagnostics["sorted"] == 0.0
    for batch, (query, target) in enumerate(zip(queries, targets)):
        assert torch.equal(before[batch, :, query, target], after[batch, :, query, target])


def test_head_specific_patch_changes_only_the_selected_head():
    attention = _attention()
    answer_queries = torch.tensor([5, 6])
    targets = torch.tensor([2, 3])
    lengthgen.PATCH = {"mode": "source_max", "head": 1, "diagnostics": {}}
    patched = lengthgen._apply_attn_patch(attention, answer_queries, targets)
    diagnostics = dict(lengthgen.PATCH["diagnostics"])
    lengthgen.PATCH = None
    assert torch.equal(attention.sort(dim=-1).values, patched.sort(dim=-1).values)
    assert diagnostics["sorted"] == 0.0
    for batch, (query, target) in enumerate(zip(answer_queries, targets)):
        assert torch.equal(attention[batch, 0, query], patched[batch, 0, query])
        assert torch.equal(attention[batch, 2, query], patched[batch, 2, query])
        expected = attention[batch, 1, query, : query + 1].max()
        assert torch.equal(patched[batch, 1, query, target], expected)


def test_multi_head_patch_changes_only_selected_heads():
    attention = _attention()
    answer_queries = torch.tensor([5, 6])
    targets = torch.tensor([2, 3])
    lengthgen.PATCH = {"mode": "source_max", "heads": [0, 2], "diagnostics": {}}
    patched = lengthgen._apply_attn_patch(attention, answer_queries, targets)
    lengthgen.PATCH = None
    assert torch.equal(attention.sort(dim=-1).values, patched.sort(dim=-1).values)
    for batch, (query, target) in enumerate(zip(answer_queries, targets)):
        assert torch.equal(attention[batch, 1, query], patched[batch, 1, query])
        for head in (0, 2):
            expected = attention[batch, head, query, : query + 1].max()
            assert torch.equal(patched[batch, head, query, target], expected)


def test_sharpened_correct_and_wrong_assignments_share_one_spectrum():
    attention = _attention()
    answer_queries = torch.tensor([5, 6])
    targets = torch.tensor([2, 3])
    outputs = {}
    for mode in ("source_max", "source_min"):
        lengthgen.PATCH = {
            "mode": mode,
            "heads": [0, 2],
            "beta": 4.0,
            "diagnostics": {},
        }
        outputs[mode] = lengthgen._apply_attn_patch(attention, answer_queries, targets)
        assert lengthgen.PATCH["diagnostics"]["sorted"] == 0.0
    lengthgen.PATCH = None
    assert torch.equal(
        outputs["source_max"].sort(dim=-1).values,
        outputs["source_min"].sort(dim=-1).values,
    )
    for batch, (query, target) in enumerate(zip(answer_queries, targets)):
        assert torch.equal(attention[batch, 1, query], outputs["source_max"][batch, 1, query])
        for head in (0, 2):
            correct = outputs["source_max"][batch, head, query, target]
            wrong = outputs["source_min"][batch, head, query, target]
            assert correct == outputs["source_max"][batch, head, query, : query + 1].max()
            assert wrong == outputs["source_min"][batch, head, query, : query + 1].min()


def test_differentiable_interpolation_matches_endpoints_and_has_gradient():
    attention = _attention()
    answer_queries = torch.tensor([5, 6])
    targets = torch.tensor([2, 3])
    heads = [0, 2]

    lengthgen.PATCH = {"mode": "source_max", "heads": heads, "diagnostics": {}}
    exact = lengthgen._apply_attn_patch(attention, answer_queries, targets)

    alpha0 = torch.zeros(2, 3, requires_grad=True)
    lengthgen.PATCH = {
        "mode": "source_max", "heads": heads, "alpha": alpha0, "diagnostics": {}
    }
    at_zero = lengthgen._apply_attn_patch(attention, answer_queries, targets)
    assert torch.equal(at_zero, attention)

    alpha1 = torch.ones(2, 3, requires_grad=True)
    lengthgen.PATCH = {
        "mode": "source_max", "heads": heads, "alpha": alpha1, "diagnostics": {}
    }
    at_one = lengthgen._apply_attn_patch(attention, answer_queries, targets)
    assert torch.equal(at_one, exact)

    alpha = torch.full((2, 3), 0.25, requires_grad=True)
    lengthgen.PATCH = {
        "mode": "source_max", "heads": heads, "alpha": alpha, "diagnostics": {}
    }
    interpolated = lengthgen._apply_attn_patch(attention, answer_queries, targets)
    loss = sum(
        interpolated[batch, :, query, target].sum()
        for batch, (query, target) in enumerate(zip(answer_queries, targets))
    )
    gradient = torch.autograd.grad(loss, alpha)[0]
    assert torch.isfinite(gradient).all()
    assert torch.count_nonzero(gradient[:, heads]) > 0
    assert torch.count_nonzero(gradient[:, 1]) == 0
    lengthgen.PATCH = None


def test_existing_forced_distribution_patch_is_unchanged():
    attention = _attention()
    answer_queries = torch.tensor([5, 6])
    targets = torch.tensor([2, 3])
    lengthgen.PATCH = {"p": 0.4, "k": 2}
    patched = lengthgen._apply_attn_patch(attention, answer_queries, targets)
    lengthgen.PATCH = None
    for batch, (query, target) in enumerate(zip(answer_queries, targets)):
        assert torch.allclose(patched[batch, :, query, target], torch.full((3,), 0.4))
        assert torch.allclose(patched[batch, :, query, :].sum(-1), torch.ones(3))


def test_multi_source_extrema_preserve_spectrum_and_move_group_mass():
    attention = torch.zeros(1, 2, 5, 5, dtype=torch.float32)
    attention[0, 0, 4] = torch.tensor([0.05, 0.10, 0.15, 0.20, 0.50])
    attention[0, 1, 4] = torch.tensor([0.40, 0.05, 0.10, 0.15, 0.30])
    query = torch.tensor([4])
    targets = torch.tensor([[1, 3]])
    outputs = {}
    masses = {}
    for mode in ("source_max", "source_min", "distractor_control"):
        lengthgen.PATCH = {"mode": mode, "diagnostics": {}}
        outputs[mode] = lengthgen._apply_attn_patch(attention, query, targets)
        diagnostics = dict(lengthgen.PATCH["diagnostics"])
        assert diagnostics["sorted"] == 0.0
        masses[mode] = outputs[mode][0, :, 4, targets[0]].sum(dim=-1)
    lengthgen.PATCH = None

    valid = attention[0, :, 4, :]
    assert torch.allclose(masses["source_max"], valid.topk(2, dim=-1).values.sum(dim=-1))
    assert torch.allclose(masses["source_min"], valid.topk(2, dim=-1, largest=False).values.sum(dim=-1))
    for head in range(valid.shape[0]):
        chosen = set(int(index) for index in valid[head].topk(2).indices)
        untouched = [index for index in range(5) if index not in chosen.union({1, 3})]
        assert torch.equal(outputs["source_max"][0, head, 4, untouched], valid[head, untouched])
    baseline_mass = valid[:, targets[0]].sum(dim=-1)
    assert torch.allclose(masses["distractor_control"], baseline_mass)


def test_pairadd_requires_two_evidence_positions_and_batches_them():
    import numpy as np

    rng = np.random.default_rng(3)
    tokens, answer_start, targets = lengthgen.make_pairadd(rng, 5, 5)
    assert len(targets) == 2
    assert len(set(targets)) == 2
    assert tokens[answer_start] == (tokens[targets[0]] + tokens[targets[1]]) % 10

    cfg = lengthgen.Cfg(task="pairadd", vocab=15, pad=lengthgen.PAIR_PAD, batch=2)
    _, _, _, _, target_batch = lengthgen.sample_batch(rng, 2, 5, 5, cfg)
    assert tuple(target_batch.shape) == (2, 2)
