# Agent Instructions

Read `PROJECT.md` and `MEMORY_MAP.md` before work, then follow the session rules below.

Use `PROJECT_FLOW.md` as the compact, read-only view of the project's Plan flow when you need historical context. The management objects remain the source of truth.

## Session responsibility

- The initial design session defines `inputs/PROJECT_SPEC.md` and its project-wide roadmap. It does not execute a Plan.
- A Plan session owns exactly one Plan from proposal through user approval, Task execution, review, and Plan completion.
- A completed Plan session must not create the next Plan. End the session after recording its result and next action.
- The next Plan is proposed and performed in a new session.

## Starting a Plan session

1. Read the full project goal, completion criteria, constraints, and roadmap in `inputs/PROJECT_SPEC.md`.
2. Read the current state and next action in `PROJECT.md`.
3. Read the most recently completed `P_XXX` object, including its goal, scope, status, and Task list. The first Plan session has no previous Plan.
4. Read that Plan's Tasks, their `remaining` and `decisions`, linked Evidence objects, and relevant Audits when needed to identify incomplete work or user decisions.
5. Select the next roadmap stage and propose its Plan scope, Tasks, and acceptance criteria to the user.
6. If the specification and actual prior result conflict, report the difference and ask the user instead of resolving it silently.
7. Before requesting approval, report the selected roadmap stage, prior Plan basis, approach, scope, ordered Tasks, risks, and acceptance criteria.
8. Save and perform the Plan only after user approval.

- Follow the approved Plan and perform one Task at a time.
- Treat `inputs/` as user-owned and read-only.
- Modify `inputs/PROJECT_SPEC.md` only when the user explicitly requests it. Never create another project specification.
- Keep originals under `ref/` immutable.
- Store implementation outputs under `src/`.
- Before creating or modifying a file, read `MEMORY_MAP.md` and the active Task's declared `outputs` and confirm the file's owner and destination.
- Declare every expected output path in the Task before execution. Create outputs at those declared paths; if the correct location is unclear, ask the user before creating a new path.
- Remove temporary files when the Task is complete. Do not leave scratch files or ad hoc directories in the project root.
- Keep the project root limited to the managed documents and directories in the canonical layout; do not create unrelated root files or directories.
- Read only files listed in the active Task's `references` unless more context is required.
- Submit results for user review. The user chooses `approve`, `revise`, `retry`, or `cancel`.
- Before submitting a Task, record and report its result: summary, actual changes, outputs, verification evidence, remaining work or known issues, and any decision needed from the user.
- Record every follow-up item in the Task's `remaining`; do not leave it only in conversation or in a separate ad hoc TODO or handoff file.
- Each submission creates a new immutable Evidence object. Never replace Evidence from an earlier attempt.
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
