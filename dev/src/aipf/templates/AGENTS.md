# Agent Instructions

Read `PROJECT.md` and `MEMORY_MAP.md` before work, then follow the session rules below.

Use `PROJECT_FLOW.md` as the compact, read-only view of the project's Plan flow when you need historical context. The management objects remain the source of truth.

## Session responsibility

- The initial design session defines `inputs/PROJECT_SPEC.md` and its project-wide roadmap. It does not execute a Plan.
- A Plan session owns exactly one Plan from proposal through user approval, Task execution, review, and Plan completion.
- A completed Plan session must not create the next Plan. End the session after recording its result and next action.
- The next Plan is proposed and performed in a new session.
- The Plan agent may execute a small Task directly or create Task subagents. Only the Plan agent may create Task agents; a Task agent must never create another Task agent.
- Invoke every Task subagent explicitly with model `gpt-5.6-luna` and reasoning effort `xhigh`.
- Run Tasks in parallel only when they have no result dependency and their declared output paths do not overlap. Otherwise run them sequentially. The Plan agent verifies and integrates every result in either case.
- If review is deferred or times out, preserve the current review state, write a clear resume action, and end the session. A new session resumes the same review rather than creating replacement work.

## Starting a Plan session

1. Read the full project goal, completion criteria, constraints, and roadmap in `inputs/PROJECT_SPEC.md`.
2. Read the current state and next action in `PROJECT.md`.
3. Read the most recently completed `P_XXX` object, including its goal, scope, status, and Task list. The first Plan session has no previous Plan.
4. Read that Plan's Tasks, their `remaining` and `decisions`, linked Evidence objects, and relevant Audits when needed to identify incomplete work or user decisions.
5. Select the next roadmap stage and propose its Plan scope, Tasks, and acceptance criteria to the user.
6. If the specification and actual prior result conflict, report the difference and ask the user instead of resolving it silently.
7. Before requesting approval, report the selected roadmap stage, prior Plan basis, approach, scope, ordered Tasks, risks, and acceptance criteria.
8. Save and perform the Plan only after user approval.

- Follow the approved Plan. A Task agent performs one Task; the Plan agent may run independent Tasks in parallel when the declared output paths and dependencies permit it.
- Treat `inputs/` as user-owned and read-only.
- Modify `inputs/PROJECT_SPEC.md` only when the user explicitly requests it. Never create another project specification.
- Keep originals under `ref/` immutable.
- Store implementation outputs under `src/`.
- Before creating or modifying a file, read `MEMORY_MAP.md` and the active Task's declared `outputs` and confirm the file's owner and destination.
- Declare every expected output path in the Task before execution. Create outputs at those declared paths; if the correct location is unclear, ask the user before creating a new path.
- Remove temporary files when the Task is complete. Do not leave scratch files or ad hoc directories in the project root.
- Keep the project root limited to the managed documents and directories in the canonical layout; do not create unrelated root files or directories.
- Read only files listed in the active Task's `references` unless more context is required.
- Return every Task result to the Plan agent for review first. The Plan agent may accept a routine result without user review when the approved scope, completion criteria, declared outputs, and verification all match. The user chooses `approve`, `revise`, `retry`, or `cancel` only when the Plan agent identifies an exception, and always confirms completion of the whole Plan.
- Telegram review is available only for one configured personal user. A review-required notification exposes `approve`, `revise`, `retry`, `cancel`, and `defer`; `revise` must preserve the user's text feedback, while `defer` ends only the current wait and leaves persisted state unchanged.
- Before sending Telegram, read `PROJECT.md` → `Telegram 알림 설정` → `전송 조건`. Run `aipf telegram wait` for Plan approval, and for a Task only when the Plan agent has identified an exception and `task_review_required` is enabled. It is a one-shot wait with a default total timeout of 600 seconds. Timeout, network failure, and interruption leave persisted state unchanged. After every Task result is accepted, present the Plan completion report and obtain explicit user confirmation before marking the Plan `completed`; use the configured review path when that confirmation is handled through Telegram.
- When the user asks to change Telegram transmission timing, edit only the comma-separated `전송 조건` line in `PROJECT.md` using the documented condition names. Use `never` alone to disable all Telegram transmission. Do not change implementation code for a project-specific preference.
- Read Telegram credentials only from environment variables. Do not add webhook, always-on daemon, multi-user, or free-form Telegram chat behavior.
- A Task agent modifies only its declared outputs and returns a structured result containing summary, actual changes, outputs, verification evidence, remaining work or known issues, and decisions needed. It does not modify Task, Evidence, runtime, or other management objects.
- The Plan agent verifies each returned result, then serially updates the Task and creates one new immutable Evidence object. It records every follow-up item in Task `remaining`; never replace Evidence from an earlier attempt. For parallel execution, it adds and removes the participating IDs in runtime `active_task_ids` and persists management objects only after each result has been reviewed.
- Request user review when the result differs from the approved Plan, fails a criterion or verification, has remaining work or a decision needed, omits an output, changes scope, introduces material risk or external impact, or cannot be confidently validated. Routine acceptance does not create an Audit. After all Task results are accepted, obtain the user's final Plan-completion confirmation.
- If a session stops after output changes but before result persistence, the next Plan session inspects those outputs and Git changes, reruns verification, and reconstructs Task and Evidence only from the reverified facts.
- Record facts, not intended work. Do not claim an unverified item succeeded; disclose differences from the approved Plan in `remaining` or `decisions`.
- Do not create an Audit for routine state changes or ordinary reviews. The Plan agent creates one only for a material project decision that future work needs to understand.
- Record execution checkpoints in the Plan's `checkpoints`. One checkpoint may cover multiple Tasks, and one Task may appear in multiple checkpoints.
- At each Plan-agent-defined execution boundary, run `aipf checkpoint create` with the Plan and participating Tasks. Declared Task outputs are included automatically; pass every additional execution path explicitly.
- Do not create a checkpoint while unrelated changes or pre-staged files exist. If file ownership is unclear, stop and ask the user.
- Restore only by checkpoint ID with `aipf checkpoint restore` on a clean working tree. Never use reset, rebase, or force-push for AIPF restoration; the CLI creates a new commit and Audit.
- Update the affected management objects and `PROJECT.md` after state changes.
- Treat `PROJECT_FLOW.md` as a read-only projection of Plans, checkpoints, material Audits, and runtime position. It intentionally omits Task and Evidence detail.
- Never edit the generated region of `PROJECT_FLOW.md` directly. The CLI refreshes only the content between its markers; content outside them may be maintained as user-facing guidance.
- Write `PROJECT.md` in Korean and other managed documents in English.
- Never store secrets in project files.

## File layout changes

- A file or directory layout change is incomplete until its ownership, access rules, and generation location are reflected in the related conventions.
- Update this `AGENTS.md`, `MEMORY_MAP.md`, `README.md`, `SKILLS.md`, `inputs/PROJECT_SPEC.md`, affected Plan, Task, Evidence, and Audit paths, and any path-dependent implementation and tests in the same change.
- Verify the updated layout and guidance before considering the change complete.
