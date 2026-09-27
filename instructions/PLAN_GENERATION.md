# Change Plan Generation

Create one plan inside each `change/<name>/CHANGE.md`. Planning never implements the Change.

## Understand intent

1. Read the full `project/PROJECT_SPEC.md`, `project/PROJECT_STATUS.md`, relevant inputs, current source, and prior decisions.
2. State the user's motivation and desired result before proposing work.
3. Connect the local Change to the overall project goal.
4. Ask about every unresolved ambiguity before creating the plan.

## Keep the scope small

Each plan item has one purpose and states:

```text
target
work
output
excluded work
verification
```

Split broad implementation or testing work. Do not include adjacent cleanup, tool replacement, or environment changes unless the user requested them.

## CHANGE.md

Write user-facing sections in Korean:

```markdown
# Change: <name>

## 사용자 의도
## 전체 목표와의 연결
## 포함 범위
## 제외 범위
## 예상 상태 변경
## Plan
## 검증 방법
## 진행 상태
## 검증 결과
## 최종 결과
```

Use one lifecycle state: `draft`, `planned`, `approved`, `running`, `review`, `awaiting_user`, `completed`, `blocked`, or `failed`. Record it under `진행 상태`. Only one agent may write an active Change at a time.

## Mandatory plan review

Invoke the Plan review defined in `VERIFICATION.md` for every Change. The attacker and defender are read-only. Reconcile their evidence, revise the plan, disclose unresolved disagreement, then ask the user to approve the plan.

Plan approval does not authorize implementation. Wait for an explicit start instruction unless the user already gave one.

If implementation changes the goal, scope, outputs, or verification, revise the plan and obtain approval again.
