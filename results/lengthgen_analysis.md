# Task: addition

Accuracy = mean exact-match across seeds [min,max]. Extrapolation = 2x/3x length.

| PE | post_attn_ln | train(1x) | 2x | 3x |
|---|---|---|---|---|
| nope | 0 | 0.00 [0.00,0.00] | 0.00 [0.00,0.00] | 0.00 [0.00,0.00] |
| nope | 1 | 0.00 [0.00,0.00] | 0.00 [0.00,0.00] | 0.00 [0.00,0.00] |
| rope | 0 | 0.97 [0.95,0.99] | 0.00 [0.00,0.00] | 0.00 [0.00,0.00] |
| rope | 1 | 0.99 [0.98,1.00] | 0.00 [0.00,0.00] | 0.00 [0.00,0.00] |

## H1: does post-attention LayerNorm improve extrapolation? (within PE)
- nope 2x: no-LN=0.00 -> LN=0.00  (delta +0.00)
- nope 3x: no-LN=0.00 -> LN=0.00  (delta +0.00)
- rope 2x: no-LN=0.00 -> LN=0.00  (delta +0.00)
- rope 3x: no-LN=0.00 -> LN=0.00  (delta +0.00)

## H2: is the LayerNorm benefit PE-dependent? (interaction)
- 2x: LN-benefit(nope)=+0.00 vs LN-benefit(rope)=+0.00 -> interaction gap +0.00
- 3x: LN-benefit(nope)=+0.00 vs LN-benefit(rope)=+0.00 -> interaction gap +0.00

## H3: does extrapolation accuracy track attention-output variance stability?
(variance-stability = layer-0 attn-out var at 3x / at train length; 1.0 = no collapse)
- nope ln0: 3x-acc=0.00 | L0 var 0.159->0.108 (stability 0.68)
- nope ln1: 3x-acc=0.00 | L0 var 0.096->0.060 (stability 0.62)
- rope ln0: 3x-acc=0.00 | L0 var 0.239->0.253 (stability 1.06)
- rope ln1: 3x-acc=0.00 | L0 var 0.067->0.066 (stability 0.98)

## Verdict (pre-registered interpretation)
- nope: mean LN benefit over {2x,3x} = +0.00  (UNINFORMATIVE: train acc < 0.8)
- rope: mean LN benefit over {2x,3x} = +0.00
- **OUTCOME 3: fix helps NEITHER informative PE.**


# recall: no result CSVs found

# Cross-task contrast: is the variance fix's benefit task-type-dependent?
- (waiting on both tasks' CSVs)


## Per-token metric probe (addition) + recall capacity diagnostic — both blocked

Attempt to recover dynamic range with a graded (per-digit) metric instead of full exact-match:

- **Addition, RoPE/no-LN, per-token accuracy**: train L5 = 1.00; **2x (L10) = 0.10; 3x (L15) = 0.09**.
  Digit chance = 0.10. So extrapolation failure is TOTAL (chance-level per digit), not partial —
  per-token gives no dynamic range because there is no partial competence to grade.
- **Recall capacity diagnostic (4 layers vs 2)**: identical ~0.4 plateau at train length
  (L5=0.39 @ step2000, same as 2-layer). Not a capacity issue; training a tiny transformer to MASTER
  associative recall is a known-hard optimization problem (MQAR). Train-length acc never reaches the
  0.8 validity gate.

**Consolidated honest status of the length-gen direction on CPU:**
- addition: baseline masters train length, fails at CHANCE for extrapolation; post-LN does not lift it
  off chance (0-vs-chance, and expected — arithmetic length-gen needs positional techniques, not a
  variance fix). Real but weak.
- recall (order-invariant positive control): baseline never masters train length on CPU, so the fix
  cannot be cleanly tested. Positive control could not be established.
- The gap itself (0.78 novelty) is NOT refuted — the blocker is COMPUTE (regime), not science or prior
  art. A GPU run (bigger model / more steps / faithful source-task reproduction) would resolve it.
