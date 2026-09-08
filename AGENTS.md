# Agent Instructions

## Required startup context

Read these files before project work:

1. `PROJECT.md` for current status and next action.
2. `MEMORY_MAP.md` for file locations, ownership, and access rules.
3. The active plan and task files referenced by `PROJECT.md`.
4. Only the `docs/` and `ref/` files listed in the active task's `references` field.

## Operating rules

- Use the user-approved plan as the source of scope.
- Perform one active task at a time unless the user explicitly requests otherwise.
- Do not edit files under `docs/`. They are user-owned reference material.
- Keep source files under `ref/` immutable. Store a new version instead of overwriting an original.
- Store implementation outputs under `src/`.
- Update the active task, its audit record, and `PROJECT.md` after meaningful state changes.
- Stop after a task result and wait for the user's `approve`, `revise`, `retry`, or `cancel` decision.
- Never store secrets in project files. Use environment variables for Telegram credentials.

## Language

- Write `PROJECT.md` in Korean for the user.
- Write all other framework-managed documents and management objects in English.

## Scope control

Do not add orchestration, multi-agent review, model routing, persistent sessions, automatic planning, or concurrency systems unless a later user-approved plan requires them.
