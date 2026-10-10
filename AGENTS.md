# AIPF Development Instructions

This checkout develops AIPF itself. Read `MEMORY_MAP.md`, `dev/instructions/COMMON.md`, and the relevant action instructions before acting.

## Development and product boundary

- `dev/` contains AIPF's own goals, status, Changes, archives, inputs, knowledge, scripts, and tests.
- `template/` is the product delivered to projects using AIPF. Its blank Spec and initial Status never describe AIPF development.
- These root instructions govern all AIPF development, including edits inside `template/`. `template/AGENTS.md` and product instructions are shipped content; do not execute their workflow while developing this repository.
- Never put AIPF development records or reference materials in `template/`.
- There is no development README. The only README is `template/README.md`, for product users.

## Minimum implementation

AIPF itself is a solo, local project. Implement only the smallest behavior the user requested. Add capabilities when actual use shows a need.

- Do not add integrity validators, speculative error guards, concurrency machinery, or automated failure-case test suites by default.
- Use Git/tool failures directly; avoid wrapping them in a second detection/recovery system.
- Check the changed behavior with a direct run and keep verification proportional to the change.
- This development constraint does not dictate the needs of projects using the product template.

## Start of every session

1. Read `dev/project/PROJECT_SPEC.md` and `dev/project/PROJECT_STATUS.md`.
2. Inspect Git status, the current branch, and recent commits.
3. If a Change is active, read `dev/change/<name>/CHANGE.md` and its `HANDOFF.md`.
4. Refresh the ignored `dev/project/PROJECT_FLOW.md` from refs defined in `dev/instructions/GIT.md`.
5. Verify file state before trusting a Handoff.

## Named status requests

| Request | Action |
|---|---|
| `현황 파악` | Report AIPF's branch, active Change, recent completion, problems, and next action. |
| `현재 계획` | Report the active development Change's intent, scope, plan, and position. |
| `전체 계획` | Report AIPF's goal and remaining roadmap from `dev/project/PROJECT_SPEC.md`. |
| `플로우` | Refresh and show `dev/project/PROJECT_FLOW.md`. |

Status requests do not change project outputs. Refreshing the ignored local Flow is permitted at session start and after ref changes.

## Action routing

Always apply `dev/instructions/COMMON.md`, then add only what the request needs.

| Request | Instruction |
|---|---|
| Create or revise a Change plan | `dev/instructions/PLAN_GENERATION.md` |
| Write or revise code | `dev/instructions/CODE_GENERATION.md` |
| Collect or fact-check information | `dev/instructions/DATA_COLLECTION.md` |
| Review a plan, source, output, or Change | `dev/instructions/VERIFICATION.md` |
| Report to the user | `dev/instructions/REPORT_GENERATION.md` |
| Branch, commit, merge, restore, push, or refresh Flow | `dev/instructions/GIT.md` |
| Generate, inspect, or publish release | `dev/instructions/RELEASE.md` and `dev/instructions/GIT.md` |
| Complete a Change | `dev/instructions/END_CHANGE.md` |
| Pause or transfer active work | `dev/instructions/HANDOFF.md` |

## Git and release

- Develop on `change/<name>` branches from `main`. Keep development records in `dev/`.
- Commit and push verified Change work, then wait for the user's final completion confirmation before archiving, merging, or publishing.
- `release` is generated, never edited directly. It contains the committed `template/` content of the accepted `main` revision at its root.
- After main publication, follow `dev/instructions/RELEASE.md`: generate local release with `bash dev/scripts/update_release_branch.sh`, then publish with `git push origin release`.
- Preserve existing release history. Never force push or publish development files. The old CLI release is replaced in the next commit, not rewritten.

## Execution boundary

- A user answer, choice, or plan approval is not an implementation command.
- If the user did not explicitly request execution, confirm once before changing project outputs.
- If the user already said to start, implement, execute, or continue an approved Change, act without asking again.
- Ask about unresolved ambiguity after inspecting relevant context.
- When changing layout, update development routing, ownership, product templates, publication rules, and affected tests together.

Use an available external Skill when its description matches the request. Do not copy external Skill instructions into this repository.

## Subagents

- Every subagent uses `gpt-5.6-luna` with `xhigh` reasoning; set both explicitly.
- A review subagent is read-only and must not create other subagents.

Never store secrets in project files. Telegram credentials come only from environment variables.
