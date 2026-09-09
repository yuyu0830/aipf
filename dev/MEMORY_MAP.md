# Project Memory Map

This file is the canonical navigation and access map for humans and AI agents. Keep it concise and update it when the managed structure changes.

## Repository boundary

The Git repository root contains `AGENTS.md`, which directs agents into `dev/` for framework development. The generated initialization example is stored separately under `example/`.

## Development root files

| Path | Purpose | User access | AI access |
|---|---|---|---|
| `../AGENTS.md` | Mandatory repository behavior and boundaries | Read/write | Read; write only on explicit user request |
| `SKILLS.md` | Reusable project workflows | Read/write | Read; write only on explicit user request |
| `PROJECT.md` | Korean status view and next action | Read; edit notification conditions | Read/write |
| `MEMORY_MAP.md` | Navigation, ownership, and access map | Read/write | Read/write |

## Development directories

| Path | Purpose | User access | AI access |
|---|---|---|---|
| `docs/` | User-owned project requirements and reference notes | Read/write | Read-only |
| `ref/` | External source originals and source metadata | Read | Read/write; originals are immutable |
| `src/` | Project implementation and generated outputs | Read/review | Read/write |
| `.aipf/plans/` | Approved and proposed project plans | Read/review | Read/write |
| `.aipf/tasks/` | Executable task contracts and results | Read/review | Read/write |
| `.aipf/audits/` | Execution events and user decisions | Read/review | Read/write, append-oriented |
| `.aipf/runtime.yaml` | Current plan, task, state, and temporary execution data | Read | Read/write |
| `.aipf/config.yaml` | Framework and Telegram notification configuration | Read/edit approved settings | Read/write within policy |

## Generated example

| Path | Purpose | User access | AI access |
|---|---|---|---|
| `../example/` | Inspectable output produced by `aipf init` | Read/review | Regenerate only for an approved framework task |

Access rules are framework policy, not operating-system permissions.

## Management objects

### Plan: `.aipf/plans/P_000.yaml`

Stores the agreed goal, scope, exclusions, acceptance criteria, task IDs, and approval state.

### Task: `.aipf/tasks/T_000.yaml`

Stores one executable unit of work, including references, outputs, constraints, verification, state, result, and evidence.

### Audit: `.aipf/audits/A_000.yaml`

Stores important state changes, execution summaries, verification evidence, and the user's `approve`, `revise`, `retry`, or `cancel` decision.

No Knowledge or persistent Session object is used. Tasks reference original files directly. Temporary execution state belongs in `.aipf/runtime.yaml`.

## Context loading order

1. Read `PROJECT.md`.
2. Read this file.
3. Read the active Plan and Task.
4. Read only paths declared in the active Task's `references`.
5. Inspect additional source files only when required by the task.

## Versioned and sensitive data

- Version project documents, plans, tasks, audits, references, and implementation outputs when appropriate.
- Do not version credentials, environment files containing secrets, caches, virtual environments, or temporary runtime artifacts.
- Keep Telegram bot token and chat ID in environment variables only.
