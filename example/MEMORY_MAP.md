# Project Memory Map

| Path | Purpose | User access | AI access |
|---|---|---|---|
| `AGENTS.md` | Agent rules | Read/write | Read; explicit-request write |
| `SKILLS.md` | Reusable workflows | Read/write | Read; explicit-request write |
| `PROJECT.md` | Korean status and next action | Read/review | Read/write |
| `MEMORY_MAP.md` | File and access map | Read/write | Read/write |
| `inputs/PROJECT_SPEC.md` | Single project-wide specification and roadmap | Read/write | Read; write only on explicit user request |
| `inputs/docs/` | User-provided documents | Read/write | Read-only |
| `inputs/codes/` | User-provided source code | Read/write | Read-only |
| `inputs/data/` | User-provided structured data | Read/write | Read-only |
| `inputs/media/` | User-provided images, audio, and video | Read/write | Read-only |
| `ref/` | External originals | Read | Manage; originals immutable |
| `src/` | Project outputs | Read/review | Read/write |
| `.aipf/plans/` | Plan objects | Review | Read/write |
| `.aipf/tasks/` | Task objects | Review | Read/write |
| `.aipf/audits/` | Events and user decisions | Review | Append-oriented write |
| `.aipf/runtime.yaml` | Current execution state | Read | Read/write |
| `.aipf/config.yaml` | Notification settings | Read/configure | Policy-limited write |

Load context in this order: `PROJECT.md`, this map, `inputs/PROJECT_SPEC.md`, active Plan, active Task, then Task references.
