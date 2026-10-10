# Working in this repository

Read `dev/DEV.md` and `dev/STATUS.md`, then check the current Git branch and working tree.

- `Dev`: AIPF's development workspace, development notes, archives, and Git publication process.
- `AIPF`: the framework delivered to user projects, maintained under `template/`.
- Follow the user's explicit label. Without a label, use clear task context; if Dev versus AIPF is ambiguous, always ask before making changes.
- These instructions govern this checkout, including edits to `template/`. Template instructions are product content, not this repository's development procedure. Never put Dev goals or records in the template.
- Keep Dev small: implement only what the user requested, check the changed behavior directly, and add tools or safeguards when an actual need arises. No mandatory Change, Handoff, review-agent, or Flow process.
- Keep brief development notes in `dev/STATUS.md`. Preserve replaced documents and important materials in dated folders under `dev/archive/`, with a note explaining their origin and replacement. Archived instructions are historical and must not govern current work.
- Preserve user edits and Git history. Never store secrets. Report to the user in Korean.

The only README is `template/README.md`. Git publication is described in `dev/DEV.md`.
