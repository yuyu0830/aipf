# Verification

Verification exists to reduce the agent's positive bias. Try to disprove the plan, source, or result before accepting it.

Run verification only when another instruction or the user calls for it. Small actions are not reviewed automatically.

## Roles

Every review uses three roles:

1. **Attacker** — assume the target is wrong; find counterexamples, omissions, conflicts, unsafe assumptions, scope drift, and failure cases.
2. **Defender** — challenge each criticism, present the strongest valid case for the target, reject false positives, and concede real defects.
3. **Main agent** — inspect original evidence, compare both sides, and decide. Do not merely summarize votes.

The attacker and defender must be separate `gpt-5.6-luna` subagents with `xhigh` reasoning. The attacker receives the original files, acceptance criteria, and observed results. The defender receives the same originals plus the attacker's exact findings. Neither receives only the main agent's summary. They are read-only and cannot spawn agents.

The attacker returns findings with `location`, `claim`, `impact`, `evidence`, and `recommended correction`. The defender answers every finding with `accepted`, `rejected`, or `partly accepted`, plus evidence. The main agent records the final decision and reason for every finding in the calling document.

## Review types

| Caller | Attack focus |
|---|---|
| `PLAN_GENERATION.md` | Misread intent, excessive scope, missing work, unverified assumptions, infeasible verification |
| `DATA_COLLECTION.md` | Fabricated source, source mismatch, stale version, irrelevant information |
| Explicit output review | Wrong inputs or outputs, missed edge cases, unexecuted checks |
| `END_CHANGE.md` | Incomplete plan, unintended changes, needless complexity, inefficient result, weak verification |

## Review conduct

- Inspect originals, Git diff, commands, and raw results directly.
- Search for failure and boundary cases before normal cases.
- Do not accept “generally looks correct” as evidence.
- Every criticism must identify its location, impact, and evidence or reproducible reasoning.
- Aggressive review must not invent defects or turn personal taste into a blocker.

## Decision

Use one result:

```text
pass
revision_required
user_decision_required
unverifiable
```

If the attacker is right, revise. If the defender is right, retain the target. If both are partly right, make the smallest justified revision. If evidence is balanced or missing, ask the user. A malformed, missing, or unavailable review never counts as a pass.
