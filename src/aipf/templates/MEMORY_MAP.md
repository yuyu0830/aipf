# Project Memory Map

| Path | Purpose | User access | AI access |
|---|---|---|---|
| `AGENTS.md` | Agent rules | Read/write | Read; explicit-request write |
| `SKILLS.md` | Reusable workflows | Read/write | Read; explicit-request write |
| `PROJECT.md` | Korean status and next action | Read/review | Read/write |
| `MEMORY_MAP.md` | File and access map | Read/write | Read/write |
| `docs/` | User project documents | Read/write | Read-only |
| `ref/` | External originals | Read | Manage; originals immutable |
| `src/` | Project outputs | Read/review | Read/write |
| `.aipf/plans/` | Plan objects | Review | Read/write |
| `.aipf/tasks/` | Task objects | Review | Read/write |
| `.aipf/audits/` | Events and user decisions | Review | Append-oriented write |
| `.aipf/runtime.yaml` | Current execution state | Read | Read/write |
| `.aipf/config.yaml` | Notification settings | Read/configure | Policy-limited write |

Load context in this order: `PROJECT.md`, this map, active Plan, active Task, then Task references.
