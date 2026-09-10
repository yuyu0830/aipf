# Project Memory Map

| Path | Purpose | User access | AI access |
|---|---|---|---|
| `AGENTS.md` | Agent rules | Read/write | Read; explicit-request write |
| `SKILLS.md` | Reusable workflows | Read/write | Read; explicit-request write |
| `PROJECT.md` | Korean status and next action | Read/review | Read/write |
| `PROJECT_FLOW.md` | Read-only projection of Plans, checkpoints, material Audits, and runtime position | Read; write outside markers | Read; refresh generated region through CLI only |
| `MEMORY_MAP.md` | File and access map | Read/write | Read/write |
| `inputs/PROJECT_SPEC.md` | Single project-wide specification and roadmap | Read/write | Read; write only on explicit user request |
| `inputs/docs/` | User-provided documents | Read/write | Read-only |
| `inputs/codes/` | User-provided source code | Read/write | Read-only |
| `inputs/data/` | User-provided structured data | Read/write | Read-only |
| `inputs/media/` | User-provided images, audio, and video | Read/write | Read-only |
| `ref/` | External originals | Read | Manage; originals immutable |
| `src/` | Project outputs | Read/review | Read/write |
| `.aipf/plans/` | Plan objects and the central execution checkpoint index | Review | Read/write |
| `.aipf/tasks/` | Task objects | Review | Read/write |
| `.aipf/evidence/` | Immutable Task submission results and verification evidence | Review | Append-only write |
| `.aipf/audits/` | Material decisions and checkpoint restoration reasons | Review | Append-oriented write |
| `.aipf/runtime.yaml` | Current execution state | Read | Read/write |
| `.aipf/config.yaml` | Notification settings | Read/configure | Policy-limited write |

Load context in this order: `PROJECT.md`, `PROJECT_FLOW.md`, this map, `inputs/PROJECT_SPEC.md`, active Plan, active Task, then Task references. Treat the flow projection as a compact index, not a replacement for source objects.

## File creation and placement rules

- Read this map before creating or modifying a file, then check the active Task's declared `outputs` and `references`.
- User-provided originals belong under `inputs/` and are read-only to AI by default. External source originals belong under `ref/` and remain immutable.
- AI-generated implementation and project deliverables belong under `src/`. Plan, Task, Evidence, Audit, and runtime management objects belong under `.aipf/`.
- `PROJECT_FLOW.md` is generated at the project root by the CLI. Do not edit its generated region directly; user-facing guidance outside the markers may be maintained separately.
- Declare output paths in the Task before execution. If no existing location clearly owns a file, ask the user before creating a directory or choosing a new path.
- Remove temporary files after the Task; do not leave scratch files or unplanned files in the project root.
- The project root is reserved for the managed documents and directories in the canonical layout. Do not add unrelated root files or directories.

## Layout synchronization

When a file or directory is added, removed, or relocated, update the related conventions in the same change. This includes `MEMORY_MAP.md`, `AGENTS.md`, `README.md`, `SKILLS.md`, `PROJECT_FLOW.md` generation rules, `inputs/PROJECT_SPEC.md`, affected Plan, Task, Evidence, and Audit paths, and path-dependent code and tests. Verify the updated layout and guidance before considering the change complete.
