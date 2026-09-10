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
| `.aipf/runtime.yaml` | Current execution and review-wait state, including transient parallel `active_task_ids`; never stores Telegram secrets | Read | Read/write |
| `.aipf/config.yaml` | Notification settings | Read/configure | Policy-limited write |

Load context in this order: `PROJECT.md`, `PROJECT_FLOW.md`, this map, `inputs/PROJECT_SPEC.md`, active Plan, active Task, then Task references. Treat the flow projection as a compact index, not a replacement for source objects.

## File creation and placement rules

- Read this map before creating or modifying a file, then check the active Task's declared `outputs` and `references`.
- User-provided originals belong under `inputs/` and are read-only to AI by default. External source originals belong under `ref/` and remain immutable.
- AI-generated implementation and project deliverables belong under `src/`. Plan, Task, Evidence, Audit, and runtime management objects belong under `.aipf/`.
- The Plan agent owns management-object updates. Task agents return structured results and do not write Task, Evidence, Audit, Plan, or runtime objects. When independent Tasks run in parallel, their transient IDs are stored in `.aipf/runtime.yaml` under `active_task_ids`; they are removed as each Task result is persisted.
- `PROJECT_FLOW.md` is generated at the project root by the CLI. Do not edit its generated region directly; user-facing guidance outside the markers may be maintained separately.
- Declare output paths in the Task before execution. If no existing location clearly owns a file, ask the user before creating a directory or choosing a new path.
- Remove temporary files after the Task; do not leave scratch files or unplanned files in the project root.
- The project root is reserved for the managed documents and directories in the canonical layout. Do not add unrelated root files or directories.

## Telegram interaction data

- `AIPF_TELEGRAM_BOT_TOKEN`, `AIPF_TELEGRAM_CHAT_ID`, and `AIPF_TELEGRAM_USER_ID` are environment variables, not project files.
- The chat ID and user ID identify the one permitted personal user and private chat. Review-required notifications use inline `approve`, `revise`, `retry`, `cancel`, and `defer` choices; `revise` feedback belongs in the existing review state and Plan/Task feedback fields, while `defer` changes no persisted state.
- `aipf telegram wait` does not create a new storage path. It performs one one-shot wait, defaults to 600 seconds, and leaves state unchanged on timeout.
- `PROJECT.md` owns the user-editable Telegram `전송 조건`; `.aipf/config.yaml` supplies initialization defaults. Agents must preserve the user's `PROJECT.md` setting during status refreshes.
- Webhooks, always-on daemons, multiple users, and free-form Telegram conversation are outside the canonical layout and current scope.

## Layout synchronization

When a file or directory is added, removed, or relocated, update the related conventions in the same change. This includes `MEMORY_MAP.md`, `AGENTS.md`, `README.md`, `SKILLS.md`, `PROJECT_FLOW.md` generation rules, `inputs/PROJECT_SPEC.md`, affected Plan, Task, Evidence, and Audit paths, and path-dependent code and tests. Verify the updated layout and guidance before considering the change complete.
