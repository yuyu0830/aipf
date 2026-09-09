# Agent Instructions

Read `PROJECT.md`, `MEMORY_MAP.md`, `inputs/PROJECT_SPEC.md`, the active Plan, and the active Task before work.

- Follow the approved Plan and perform one Task at a time.
- Treat `inputs/` as user-owned and read-only.
- Modify `inputs/PROJECT_SPEC.md` only when the user explicitly requests it. Never create another project specification.
- Keep originals under `ref/` immutable.
- Store implementation outputs under `src/`.
- Read only files listed in the active Task's `references` unless more context is required.
- Submit results for user review. The user chooses `approve`, `revise`, `retry`, or `cancel`.
- Update Task, Audit, and `PROJECT.md` after state changes.
- Write `PROJECT.md` in Korean and other managed documents in English.
- Never store secrets in project files.
