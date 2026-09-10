# Project Direction

## Purpose

AIPF helps a user conduct an AI-assisted project through files that remain understandable without the original conversation.

The user and AI agree on a plan, save executable tasks, perform one task, review its result, and continue from persisted project state.

## Primary workflow

```text
initial design session -> save project specification and roadmap
plan session -> inspect prior result -> agree and save one plan -> report plan -> approve plan
             -> execute one task -> verify result -> report actual result -> user review
             -> record material decisions when needed -> complete plan -> end session
next plan session or explicit user-confirmed project completion
```

## Product focus

- A Korean `PROJECT.md` that clearly shows current status and the next action.
- A read-only `PROJECT_FLOW.md` that gives a compact view of Plans, checkpoints, material Audits, and current runtime state.
- Human-readable Plan, Task, Evidence, and Audit objects.
- A file layout that reveals how the project operates.
- Direct references to user documents and external source originals.
- One natural-language project specification with a project-wide roadmap.
- An inspectable pre-execution Plan report and fact-based Task completion report.
- File-creation conventions that keep generated project files in their canonical locations.
- Minimal AI task execution with user-controlled acceptance.
- Recovery from the current persisted state.
- One Plan per execution session, from proposal through completion.
- Optional Telegram notifications.

## Design principles

- Files are the source of project continuity.
- The user approves plans and task results.
- Plans state their selected roadmap stage, prior-result basis, approach, and risks before approval.
- Task results distinguish actual changes, outputs, verification evidence, remaining work, and user decisions.
- Plan objects centrally index execution checkpoints by stable checkpoint ID and the Tasks included in each execution.
- A checkpoint commit includes the Plan index, affected management objects, and declared execution outputs. Unowned changes stop checkpoint creation.
- Restoring a checkpoint recreates that checkpoint's state in a new commit, preserves Git history and append-only records, and records the reason in an Audit.
- Routine state transitions are not Audits; the Plan agent records only material project decisions that future work needs.
- `PROJECT_FLOW.md` is a derived, read-only projection rather than a source of truth. It excludes Task and Evidence detail and is refreshed by the CLI after state changes.
- The CLI owns only the generated region between the flow markers; it preserves any content outside those markers and agents do not edit the generated region directly.
- A completed Plan session does not create the next Plan; a new session continues from persisted state.
- Project completion is an explicit user decision after all roadmap stages are done.
- The framework does not automatically decompose goals into tasks.
- The framework does not replace original sources with generated knowledge summaries.
- File placement is a generation convention: follow the canonical layout and `MEMORY_MAP.md`; when a suitable location is unclear, ask before inventing a new directory.
- A file-layout change is complete only when the canonical layout, all path-bearing templates (`AGENTS.md`, `MEMORY_MAP.md`, `README.md`, `SKILLS.md`, and `PROJECT_SPEC.md`), affected code and tests, and the CLI-generated `example/` are synchronized in the same change.
- Add new mechanisms only after project use demonstrates a need.
- Prefer direct, inspectable state over hidden orchestration.

## Canonical layout

```text
project-root/
|-- AGENTS.md
|-- SKILLS.md
|-- PROJECT.md
|-- PROJECT_FLOW.md
|-- MEMORY_MAP.md
|-- inputs/
|   |-- PROJECT_SPEC.md
|   |-- docs/
|   |-- codes/
|   |-- data/
|   `-- media/
|-- ref/
|-- src/
`-- .aipf/
    |-- plans/P_000.yaml
    |-- tasks/T_000.yaml
    |-- evidence/E_000.yaml
    |-- audits/A_000.yaml
    |-- runtime.yaml
    `-- config.yaml
```

See `MEMORY_MAP.md` for ownership and access rules. Changes to this layout must update the related guidance, implementation, tests, and generated example together.

## Future direction

Future plans may add capabilities when a real project requires them. Candidate capabilities include richer recovery, additional providers, controlled parallel execution, or specialized review. They are not part of the core structure by default.
