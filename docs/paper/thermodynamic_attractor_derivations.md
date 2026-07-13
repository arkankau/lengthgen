# Thermodynamic Attractor Derivations

Purpose: define candidate attractors as math objects before running more generation experiments. The goal is not to claim these are solved defenses. The goal is to identify which thermodynamic mechanism each candidate tests, what observables it should change, and what failure mode would falsify it.

## Common Setup

Let a transformer attention head receive queries `Q`, keys `K`, values `V`, and hidden trajectory state `X`.

For token `i` attending to token/state `j`:

```text
z_ij = beta * q_i dot k_j / sqrt(d) + b_j - Phi_ij(Q, K, X)
p_ij = softmax_j(z_ij)
y_i  = sum_j p_ij v_j
```

Thermodynamic reading:

```text
E_ij = -q_i dot k_j / sqrt(d) - b_j / beta + Phi_ij / beta
p_ij proportional to exp(-beta E_ij)
F = E - T S
T = 1 / beta
```

Risk enters through a scalar or latent functional:

```text
R(X) in [0, 1]
g_R = sigmoid(kappa * (R(X) - R_c))
```

Core observables:

```text
m_A      = attention mass assigned to attractor A
H        = -sum_j p_j log p_j
Delta    = spectral gap / concentration proxy
Psi_A    = m_A - max_non_attractor_mass
sep_A    = mean(m_A | jailbreak) - mean(m_A | benign)
```

Good thermodynamic control should increase risky-selective `m_A` or barrier effects while preserving benign entropy and useful language. Global collapse means high attractor mass with low entropy and poor or repetitive continuations.

## 1. Null Attractor

Add a synthetic key/value pair `(k_null, v_null)` and lower its energy when risk is high.

```text
K' = [K; k_null]
V' = [V; v_null]
b_null(X) = eta_null * g_R
z_i,null = beta * q_i dot k_null / sqrt(d) + b_null(X)
```

If `k_null = 0` and `v_null = 0`, this becomes a risk-gated absorbing sink:

```text
p_i,null = exp(b_null) / (sum_j exp(z_ij) + exp(b_null))
```

Expected diagnostic:

```text
R(X) crosses R_c -> m_null rises sharply
susceptibility chi = d m_null / d R peaks near R_c
```

Interpretation:

The null attractor tests whether the model is susceptible to a controlled low-energy basin under risky states.

Failure mode:

High `m_null` plus low entropy and bad continuations means global degeneration, not safety. This is exactly why null attraction is useful as a diagnostic but weak as generation control.

## 2. Refusal Attractor

Replace the empty basin with a semantic basin estimated from refusal hidden states.

Let:

```text
mu_refuse = mean hidden/value states from safe refusal completions
mu_unsafe = mean hidden/value states from unsafe compliant completions
r_refuse  = normalize(mu_refuse - mu_unsafe)
```

Use this direction as either a value attractor or residual steering vector:

```text
v_A = alpha * r_refuse
y_i = sum_j p_ij v_j + lambda_R * r_refuse
lambda_R = lambda * g_R
```

Energy view:

```text
E_refuse(x) = -cos(x, r_refuse)
F_refuse(x) = E_refuse(x) - T S_safe(x)
```

Expected diagnostic:

Risky prompts should show increasing alignment with `r_refuse`, but benign prompts should not be pulled into refusal.

```text
a_refuse(X) = cos(h_last, r_refuse)
sep_refuse = mean(a_refuse | jailbreak) - mean(a_refuse | benign)
```

Expected intervention behavior:

Unlike null, the attractor writes semantic safety content into the residual stream. It can still fail if refusal is not one-dimensional or if the steering layer/head is wrong.

Failure mode:

Template refusals for benign prompts imply over-attraction. Unsafe continuations despite high `a_refuse` imply the direction is not causally sufficient.

## 3. Safe-Redirection Attractor

Pure refusal can be safe but unhelpful. Define an attractor for refusal plus useful safe alternative.

Construct two centroids:

```text
mu_refuse   = mean states from direct refusal
mu_redirect = mean states from safe educational / prevention / high-level alternatives
```

Use a mixture attractor:

```text
a_safe = w_refuse * normalize(mu_refuse)
       + w_redirect * normalize(mu_redirect)
w_refuse + w_redirect = 1
```

Risk-dependent mixture:

```text
w_refuse(R)   = sigmoid(gamma * (R - R_hard))
w_redirect(R) = 1 - w_refuse(R)
```

For moderately risky prompts, the attractor favors helpful redirection. For highly risky prompts, it favors stronger refusal.

Energy:

```text
E_safe(x, R) = -cos(x, a_safe(R))
```

Expected behavior:

```text
jailbreak -> safe refusal or safe alternative
benign    -> normal answer, low attraction
ambiguous -> redirection rather than nonsense
```

Failure mode:

If outputs become generic templates, the attractor is too narrow. If outputs become nonsense, the value geometry is not aligned with the model's generation manifold.

## 4. High-Entropy Safety Shell

Instead of pulling to one basin, prevent risky prompts from collapsing into a narrow unsafe basin.

Jailbreak-like behavior can be modeled as a low-entropy commitment:

```text
H(p_i) = -sum_j p_ij log p_ij
collapse if H is low and unsafe coupling is high
```

Define a target entropy band:

```text
H_min(R) = H_0 + rho * g_R
L_shell = max(0, H_min(R) - H(p_i))^2
```

Equivalent logit operation:

```text
beta_eff(R) = beta / (1 + tau * g_R * unsafe_score)
```

This locally raises temperature for risky unsafe collapse, keeping multiple safe alternatives alive.

Expected diagnostic:

The safety shell should reduce spectral-gap spikes and prevent single-basin domination.

```text
global degeneration: H -> low, Delta -> high, bad output
controlled shell:    H stays moderate, unsafe coupling falls
```

Failure mode:

Too much entropy produces vague or incoherent output. The shell is a stabilizer, not a full semantic policy.

## 5. Free-Energy Barrier Against Unsafe Couplings

Instead of adding an attractor, raise the energy of unsafe paths.

Let `u` be an unsafe direction, classifier vector, or latent risk probe gradient. Define an unsafe coupling score:

```text
C_unsafe(i, j) = sigma(q_i dot u_q) * sigma(k_j dot u_k)
```

Add a risk-scaled penalty:

```text
Phi_ij(Q, K, X) = lambda_phi * g_R * C_unsafe(i, j)
z_ij' = z_ij - Phi_ij
```

Energy:

```text
E_ij' = E_ij + Phi_ij / beta
```

Thermodynamic meaning:

Unsafe completions require crossing a higher free-energy barrier. The model is not told to collapse into null; it is discouraged from retrieving unsafe states.

Expected behavior:

```text
unsafe attention paths lose probability mass
benign task paths remain available
entropy should not globally collapse
```

Failure mode:

If the barrier is too broad, it blocks benign technical content. If too narrow, jailbreak paths route around it.

## 6. Metastable Safety Basin

A good safety process may not jump directly from risk to refusal. It may pass through an intermediate evaluation state.

Define three basins:

```text
B_task    = normal task-solving basin
B_eval    = safety-evaluation basin
B_refuse  = refusal/redirection basin
```

Risk changes the transition rates:

```text
P(B_task -> B_eval)   increases with R(X)
P(B_eval -> B_refuse) increases with confirmed unsafe coupling
P(B_eval -> B_task)   remains possible for benign/false alarms
```

A simple energy model:

```text
E_task(R)   = E_task0 + a_task * R
E_eval(R)   = E_eval0 - a_eval * R
E_refuse(R) = E_refuse0 - a_refuse * confirmed_unsafe(X)
```

Metastability condition:

```text
E_eval < E_task for risky prompts
E_refuse < E_eval only when unsafe evidence persists
```

Expected diagnostic:

Risky prompts should show transient attraction to evaluation heads/states before final redirection. Benign prompts should escape back to task-solving.

Failure mode:

If `B_eval` becomes absorbing, the model gives generic hedging. If it is too shallow, jailbreaks bypass safety evaluation.

## 7. Energy Landscape Reshaping

Generalize attractor design as changing the relative depth of basins.

For candidate basins:

```text
B_benign, B_unsafe, B_refuse, B_redirect
```

Define basin energies:

```text
E_b(X) = -cos(h(X), c_b)
```

where `c_b` is a centroid or learned direction for basin `b`.

A good safety transformation should satisfy:

```text
For jailbreak:
E_refuse or E_redirect < E_unsafe

For benign:
E_benign < E_refuse

For all:
H not globally collapsed
```

This gives the cleanest comparison table:

```text
method              lowers safe energy   raises unsafe energy   preserves benign basin
null attractor      no semantic content  no                     often no
refusal attractor   yes                  weak/no                 maybe
safe redirection    yes                  weak/no                 better target
entropy shell       indirect             indirect                maybe
barrier Phi         no                   yes                    maybe
landscape reshape   yes                  yes                    target ideal
```

## Recommended Experimental Order

1. Keep null attractor as the diagnostic baseline.
2. Implement refusal and safe-redirection attractor scoring first, without generation intervention.
3. Add barrier `Phi(Q,K,X)` as an attention-logit penalty and test whether it avoids global degeneration.
4. Only then run generation bakeoffs.

The immediate paper claim should be:

> Null attraction revealed the thermodynamic response, but safe control requires structured attractors or barriers that reshape the energy landscape without destroying benign task basins.

