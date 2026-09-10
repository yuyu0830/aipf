# Project Direction

## Purpose

AIPF helps a user conduct an AI-assisted project through files that remain understandable without the original conversation.

The user and AI agree on a plan, save executable tasks, let the Plan agent verify their results, request user review only when needed, and continue from persisted project state.

## Primary workflow

```text
initial design session -> save project specification and roadmap
plan session -> inspect prior result -> agree and save one plan -> report plan -> approve plan
             -> execute independent tasks in parallel when safe, otherwise sequentially
             -> Plan-agent verification -> accept routine results or request exception review
             -> record material decisions when needed -> user confirms Plan completion -> end session
next plan session or explicit user-confirmed project completion
```

## Product focus

- A Korean `PROJECT.md` that clearly shows current status and the next action.
- A read-only `.aipf/PROJECT_FLOW.md` that gives a compact view of Plans, checkpoints, material Audits, and current runtime state.
- Human-readable Plan, Task, Evidence, and Audit objects.
- A file layout that reveals how the project operates.
- Direct references to user documents and external source originals.
- One natural-language project specification with a project-wide roadmap, stored as user-owned guidance.
- An optional user-authored code conventions document that code Tasks read only when writing, modifying, or reviewing code.
- An inspectable pre-execution Plan report and fact-based Task completion report.
- File-creation conventions that keep generated project files in their canonical locations.
- Minimal AI task execution with Plan-controlled acceptance and user review for exceptions and Plan completion.
- Recovery from the current persisted state.
- One Plan per execution session, from proposal through completion.
- Optional Telegram notifications and review interaction for one configured personal user.

## Design principles

- Files are the source of project continuity.
- The user approves Plans, reviews Task results when the Plan agent identifies an exception, and confirms Plan completion.
- Plans state their selected roadmap stage, prior-result basis, approach, and risks before approval.
- Task results distinguish actual changes, outputs, verification evidence, remaining work, and user decisions.
- Plan objects centrally index execution checkpoints by stable checkpoint ID and the Tasks included in each execution.
- A checkpoint commit includes the Plan index, affected management objects, and declared execution outputs. Unowned changes stop checkpoint creation.
- Restoring a checkpoint recreates that checkpoint's state in a new commit, preserves Git history and append-only records, and records the reason in an Audit.
- Routine state transitions are not Audits; the Plan agent records only material project decisions that future work needs.
- `.aipf/PROJECT_FLOW.md` is a derived, read-only projection rather than a source of truth. It excludes Task and Evidence detail and is refreshed by the CLI after state changes.
- The CLI owns only the generated region between the flow markers; it preserves any content outside those markers and agents do not edit the generated region directly.
- A completed Plan session does not create the next Plan; a new session continues from persisted state.
- Only the Plan agent may create Task agents. Task agents must not create other Task agents. Every subagent invocation explicitly uses `gpt-5.6-luna` with `xhigh` reasoning.
- The Plan agent may perform a small Task directly. Otherwise it runs independent Tasks in parallel when their outputs do not overlap and neither depends on the other's result; all other Tasks run sequentially. The Plan agent remains responsible for integration and verification.
- Parallel execution membership belongs in runtime `active_task_ids`, not in the durable Plan object. Task agents return structured results; only the Plan agent validates them and writes Task and Evidence objects serially.
- The Plan agent reviews every Task result before any user review. It accepts a routine result when the approved scope, completion criteria, declared outputs, and verification are all satisfied. It requests user review when the result differs from the approved Plan, fails a criterion or verification, has remaining work or a decision needed, omits an output, changes scope, introduces material risk or external impact, or cannot be confidently validated. Routine acceptance does not create an Audit; the user still confirms completion of the whole Plan.
- Before acting, the agent asks the user about unresolved ambiguity when it could materially change the goal, scope, outputs, acceptance criteria, risk, cost, reversibility, or external impact. It may choose reversible details supported by project context, but records material assumptions in the Plan report or Task result. If clarification changes an approved Plan, the Plan is revised and approved again before execution.
- If a session ends after output changes but before the Plan agent persists the result, the next session distrusts conversational handoff, inspects the outputs and Git changes, reruns verification, and only then reconstructs the missing Task and Evidence state.
- A deferred or timed-out review ends the current session after persisted state and the resume action are made clear. A new session resumes the same review from files.
- Project completion is an explicit user decision after all roadmap stages are done.
- The framework does not automatically decompose goals into tasks.
- The framework does not replace original sources with generated knowledge summaries.
- Telegram review interaction is limited to the configured personal user. Review-required notifications provide `approve`, `revise`, `retry`, `cancel`, and `defer` buttons; `revise` requires user feedback. `defer` ends the current wait without changing persisted state so review can resume later.
- `aipf telegram wait` is a one-shot long-polling command for an active review. Its default total wait is 600 seconds. A timeout exits without changing Plan, Task, or project state.
- `PROJECT.md` is the user-facing source for Telegram transmission conditions. Plan and Task agents read its `전송 조건` line before sending; the user may change that comma-separated line by direct edit or request without changing code.
- Telegram credentials are read only from environment variables. Webhooks, an always-on daemon, and free-form Telegram conversation are outside the framework scope.
- File placement is a generation convention: follow the canonical layout and `.aipf/instructions/MEMORY_MAP.md`; when a suitable location is unclear, ask before inventing a new directory.
- `inputs/` contains only user-provided project originals. `guidance/` contains user-owned project direction and optional code conventions; AI writes it only on explicit request. Plan sessions read `guidance/PROJECT_SPEC.md`, and code Tasks read `guidance/CODE_CONVENTIONS.md`; other Tasks do not read the code conventions file.
- A file-layout change is complete only when the canonical layout, all path-bearing templates (root `AGENTS.md`, `.aipf/instructions/AGENTS.md`, `.aipf/instructions/MEMORY_MAP.md`, `README.md`, `.aipf/instructions/SKILLS.md`, `guidance/PROJECT_SPEC.md`, and `guidance/CODE_CONVENTIONS.md`), affected code and tests, and the CLI-generated `example/` are synchronized in the same change.
- Add new mechanisms only after project use demonstrates a need.
- Prefer direct, inspectable state over hidden orchestration.

## Canonical layout

```text
project-root/
|-- AGENTS.md
|-- PROJECT.md
|-- inputs/
|   |-- docs/
|   |-- codes/
|   |-- data/
|   `-- media/
|-- guidance/
|   |-- PROJECT_SPEC.md
|   `-- CODE_CONVENTIONS.md
|-- ref/
|-- src/
`-- .aipf/
    |-- instructions/
    |   |-- AGENTS.md
    |   |-- SKILLS.md
    |   `-- MEMORY_MAP.md
    |-- PROJECT_FLOW.md
    |-- plans/P_000.yaml
    |-- tasks/T_000.yaml
    |-- evidence/E_000.yaml
    |-- audits/A_000.yaml
    |-- runtime.yaml
    `-- config.yaml
```

See `.aipf/instructions/MEMORY_MAP.md` for ownership and access rules. Changes to this layout must update the related guidance, implementation, tests, and generated example together.

## Future direction

Future plans may add capabilities when a real project requires them. Candidate capabilities include richer recovery, additional providers, or specialized review. They are not part of the core structure by default.
