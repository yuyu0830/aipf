# Project Memory Map

Read this file before creating or moving a file. If a destination is unclear, ask instead of inventing a directory.

## Sources of truth

| Question | Source |
|---|---|
| What does the user ultimately want? | `project/PROJECT_SPEC.md` |
| What is currently accepted and complete? | `project/PROJECT_STATUS.md` |
| What is the current branch changing? | Its `change/<name>/CHANGE.md` |
| How can interrupted work resume? | Its `HANDOFF.md`, verified against files and Git |
| What happened historically? | Git commits, completion tags, and `archive/` |

`project/PROJECT_FLOW.md` is only a local view. Handoff text is only a resume hint. Neither overrides Git, the approved Change, or Project Status.

| Path | Purpose | Agent access |
|---|---|---|
| `project/PROJECT_SPEC.md` | User goal, requirements, and roadmap | Read; edit only on explicit request |
| `project/old/` | Prior accepted Project Specs | Read; append before replacing the current spec |
| `project/PROJECT_STATUS.md` | Current result, concise history, remaining work, next action | Read/write |
| `project/PROJECT_FLOW.md` | Local Mermaid view derived from Git | Generate locally; never commit |
| `instructions/` | User-editable agent rules | Read; edit only on explicit request |
| `change/<name>/` | One active Change and Handoff | Read/write on its branch |
| `archive/` | Completed Change folders | Read; append at Change completion |
| `inputs/` | Latest user references and older revisions | Read/write by explicit request or approved Change |
| `knowledge/` | Reusable verified information; no downloaded originals | Read/write through data collection rules |
| `src/CURRENT_VERSION` | Version selected by the single entry point | Read/write through an approved Change |
| `src/vN/` | Code for implementation version `vN` | Read/write through an approved Change |
| `src/vN/result/run_NNN/` | One execution result and Korean `RUN.md` | Append during an approved run |

## Placement rules

- Keep the latest input in its category directory. Before replacing it, move the prior revision to `old/<stem>_NNN.<ext>` using the next unused number. Never overwrite an older revision.
- Do not read `old/` by default.
- Create `tests/` only when an approved Change needs automated tests.
- Keep one project entry point. It reads `src/CURRENT_VERSION`; no command-line or environment override selects a version.
- Do not share code across `src/vN/` versions unless the user approves it in the Change plan.
- Store external URLs and verified summaries in `knowledge/`; do not download external originals.
- Every execution creates the next unused `src/vN/result/run_NNN/`. Its Korean `RUN.md` records version, date, input, command, outputs, and success or failure. Never overwrite an earlier run.
- Keep temporary files outside the repository and remove them after use.
