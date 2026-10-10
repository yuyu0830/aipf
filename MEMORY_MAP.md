# AIPF Development Memory Map

Read this map before creating or moving files. Paths are relative to the development repository root. If a destination is unclear, ask instead of inventing a directory.

## Sources of truth

| Question | Source |
|---|---|
| What should AIPF itself become? | `dev/project/PROJECT_SPEC.md` |
| What is accepted and complete in AIPF? | `dev/project/PROJECT_STATUS.md` |
| What is this branch changing? | `dev/change/<name>/CHANGE.md` |
| How can development resume? | Its `HANDOFF.md`, verified against files and Git |
| What happened previously? | Git, completion tags, and `dev/archive/` |
| What does an AIPF user receive? | The committed `template/` tree |
| How is release generated? | `dev/instructions/RELEASE.md` |

`dev/project/PROJECT_FLOW.md` is only a local view. Handoff text is a resume hint. Neither overrides Git, the approved Change, or development Status.

## Ownership and placement

| Path | Purpose | Agent access |
|---|---|---|
| `AGENTS.md`, `MEMORY_MAP.md` | Development routing and ownership | Edit on explicit request or approved instruction/layout Change |
| `dev/project/PROJECT_SPEC.md` | AIPF goals, requirements, roadmap | Read; edit only on explicit request |
| `dev/project/old/` | Prior accepted development Specs | Append before replacing the development Spec |
| `dev/project/PROJECT_STATUS.md` | Accepted result, active Change, next action | Read/write |
| `dev/project/PROJECT_FLOW.md` | Development Git flow | Generate locally; never commit |
| `dev/instructions/` | Rules for developing AIPF | Edit only on explicit request |
| `dev/change/<name>/` | Active AIPF Change and Handoff | Read/write on its branch |
| `dev/archive/` | Completed AIPF Changes | Read; append at completion; retain historical record text |
| `dev/inputs/` | References for AIPF development | Write by explicit request or approved Change |
| `dev/knowledge/` | Reusable verified development information | Write through data collection rules |
| `dev/scripts/` | Development and publication tools | Write through approved Change |
| `dev/tests/` (optional) | Tests justified by an actual development need | Do not create a standing validation suite by default |
| `template/` | Independent ready-to-clone product tree | Edit through approved AIPF Change |
| `template/project/PROJECT_SPEC.md` | Blank user-project Spec | Keep as template; never insert AIPF goals |
| `template/project/PROJECT_STATUS.md` | Initial user-project Status | No AIPF completion records |
| `template/change/`, `template/archive/`, `template/inputs/`, `template/knowledge/`, `template/src/` | Initial user-project spaces | No AIPF development outputs or references |
| `template/project/PROJECT_FLOW.md` | Local product preview, if needed | Ignored; never distribute |
| `template/README.md` | The only README, for product users | Update with related product changes |

## Rules

- Root management folders such as `project/`, `change/`, `archive/`, and `src/` must not reappear in the development checkout.
- Product instructions describe paths relative to the released project root. Do not prefix shipped paths with `template/`.
- Apply the root router and `dev/instructions/` even when editing product instructions. Never treat blank product state as development state.
- Keep latest development input in its category directory. Before replacement preserve it as `old/<stem>_NNN.<ext>` using the next unused number. Do not read `old/` by default.
- Store URLs and verified summaries in `dev/knowledge/`; do not download external originals or store secrets.
- Keep temporary files outside the repository and remove them after use.
- `release` is generated, not a second editable source tree. Publish only the committed `template/` tree under `dev/instructions/RELEASE.md`.
