# Project Direction

## Purpose

AIPF helps a user conduct an AI-assisted project through files that remain understandable without the original conversation.

The user and AI agree on a plan, save executable tasks, perform one task, review its result, and continue from persisted project state.

## Primary workflow

```text
agree -> save plan and tasks -> approve plan -> execute one task
      -> verify result -> user review -> audit decision -> continue
```

## Product focus

- A Korean `PROJECT.md` that clearly shows current status and the next action.
- Human-readable Plan, Task, and Audit objects.
- A file layout that reveals how the project operates.
- Direct references to user documents and external source originals.
- Minimal AI task execution with user-controlled acceptance.
- Recovery from the current persisted state.
- Optional Telegram notifications.

## Design principles

- Files are the source of project continuity.
- The user approves plans and task results.
- The framework does not automatically decompose goals into tasks.
- The framework does not replace original sources with generated knowledge summaries.
- Add new mechanisms only after project use demonstrates a need.
- Prefer direct, inspectable state over hidden orchestration.

## Canonical layout

```text
project-root/
|-- AGENTS.md
|-- SKILLS.md
|-- PROJECT.md
|-- MEMORY_MAP.md
|-- docs/
|-- ref/
|-- src/
`-- .aipf/
    |-- plans/P_000.yaml
    |-- tasks/T_000.yaml
    |-- audits/A_000.yaml
    |-- runtime.yaml
    `-- config.yaml
```

See `MEMORY_MAP.md` for ownership and access rules.

## Future direction

Future plans may add capabilities when a real project requires them. Candidate capabilities include richer recovery, additional providers, controlled parallel execution, or specialized review. They are not part of the core structure by default.
