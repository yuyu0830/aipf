# Working in this repository

Start with only `dev/Requests.md` and `dev/Status.md`, then check the current Git branch and working tree. Read `dev/DEV.md` for Git or publication work, and search `dev/History.md` only when past context is needed. Retrieve original documents from Git when necessary. Do not preload history or template instructions.

- `Dev`: AIPF's development workspace, development notes, improvement history, and Git publication process.
- `AIPF`: the framework delivered to user projects, maintained under `template/`.
- Follow the user's explicit label. Without a label, use clear task context; if Dev versus AIPF is ambiguous, always ask before making changes.
- These instructions govern this checkout, including edits to `template/`. Template instructions are product content, not this repository's development procedure. Never put Dev goals or records in the template.
- Keep Dev small: implement only what the user requested, check the changed behavior directly, and add tools or safeguards when an actual need arises. No mandatory Change, Handoff, review-agent, or Flow process.
- Commit and push only at meaningful checkpoints or on the user's explicit request. Accumulate small related edits; a file edit or the end of a conversation turn is not a checkpoint. Follow `dev/DEV.md` for Git usage.
- Keep new ideas and unstarted requests in `dev/Requests.md`; keep only active work, agreed scope, and the next action in `dev/Status.md`. Agreement with an idea is not an instruction to implement it; an explicit instruction to apply the agreed scope is sufficient to start.
- On completion, summarize the date, result, reason, and related commits in `dev/History.md`, then remove the active entry from Status. Requests and Status are the routine working notes; update History when work finishes. Preserve original documents in Git rather than maintaining a separate Dev archive. Historical instructions must not govern current work.
- Preserve user edits and Git history. Never store secrets. Report to the user in Korean.

The only README is `template/README.md`. Git publication is described in `dev/DEV.md`.
