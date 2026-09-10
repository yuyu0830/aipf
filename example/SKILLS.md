# Project Workflows

## Task delegation

Only the Plan agent creates Task agents. It may perform a small Task directly. Delegate independent Tasks in parallel only when they have no result dependency and no overlapping declared output path; otherwise execute them sequentially. Record in-flight parallel membership in runtime `active_task_ids`, not the durable Plan object. Task agents never create Task agents. Every delegated Task explicitly uses `gpt-5.6-luna` with reasoning effort `xhigh`. The Plan agent integrates and verifies all returned results.

## Plan

Agree on goal, scope, outputs, acceptance criteria, constraints, references, and Task order. Save only after showing the user a final preview. Do not execute before approval. After all Task results have been accepted, request the user's final confirmation before marking the Plan complete.
Resolve material ambiguity before execution; if clarification changes an approved Plan, revise and obtain approval again.

## Code conventions

For code writing, modification, or review Tasks, read and follow the user's rules in `guidance/CODE_CONVENTIONS.md`; do not invent project-wide code conventions when it is empty.

## Task

Read the active Task and its references. Create only declared outputs under `src/`, run declared verification, and return summary, changes, outputs, verification, remaining work, and decisions to the Plan agent. Do not modify management objects or create Evidence. The Plan agent verifies and persists the result. The Plan agent requests user review only when the result differs from the approved scope, fails a criterion or verification, leaves remaining work or a decision needed, omits an output, changes scope, introduces material risk or external impact, or cannot be confidently validated. Routine accepted results need no user review or Audit.

## Review

- `approve`: accept a result requiring user review and continue.
- `revise`: save user feedback and repeat the Task.
- `retry`: repeat the unchanged Task.
- `cancel`: cancel the Task and stop the project.
- Routine valid results are accepted by the Plan agent without a user review. The user still confirms final Plan completion.

Telegram review uses one configured personal user and private chat, identified by `AIPF_TELEGRAM_CHAT_ID` and `AIPF_TELEGRAM_USER_ID`. It offers `approve`, `revise`, `retry`, `cancel`, and `defer`; `defer` ends only the current wait without changing persisted state. Run `aipf telegram wait` only for an active review; it waits once for up to 600 seconds by default. Store `revise` text as review feedback, and read all Telegram credentials from environment variables only. Webhooks, always-on daemons, multi-user access, and free-form Telegram chat are excluded.

Before invoking Telegram, read the comma-separated `전송 조건` in `PROJECT.md`. `plan_review_required` enables Plan approval messages and replies; `task_review_required` enables Task result messages and replies. Completion and blockage notifications use `task_completed`, `plan_completed`, and `blocked`. `never` must appear alone and disables all transmission. A user request to change transmission timing is fulfilled by editing this line, not framework code.

## Checkpoint

At each Plan-agent-defined execution boundary, create one checkpoint for the execution and list every participating Task. A checkpoint may include multiple Tasks from one parallel batch, and a Task may participate in multiple checkpoints. Task outputs are included from their declarations; list any additional execution paths explicitly. Checkpoint creation must stop if the Git staging area already contains changes or if another working-tree change has no confirmed owner.

Restore only from a clean working tree and only by a recorded checkpoint ID. A restore recreates that checkpoint state in a new commit, preserves the checkpoint index and append-only Evidence and Audit history, and records the restoration reason in a new Audit. Do not use destructive Git history rewriting.

## Project flow projection

`PROJECT_FLOW.md` is a read-only projection of Plans, checkpoints, material Audits, and the current runtime position. It intentionally excludes Task and Evidence detail. The AIPF CLI refreshes only the generated region between its markers; preserve content outside the markers and never edit the generated region directly. Use normal CLI state-changing commands or `status` to refresh the projection.

## Reference source

Store originals under `ref/` without overwriting them. Add a sidecar `*.source.yaml` with source URL, retrieval time, title, license when known, checksum, and related Task IDs.
