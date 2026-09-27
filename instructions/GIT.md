# Git

Git history is the durable source for branches, completion points, and recovery. Agents perform these procedures directly; there is no AIPF daemon.

## Change branches

- Create one `change/<name>` branch from the intended base commit.
- A branch has one active Change. Only one writing agent may operate on it.
- Validate the name, confirm it does not already exist, and record the base commit in `CHANGE.md`.
- Commit automatically after meaningful verified work. Include only files owned by the Change.
- Never amend another author's commit or use force push.

## Before every Git write

Check the current branch, HEAD, upstream, working tree, staged files, remote divergence, and file ownership. Stop for dirty or staged files not owned by the Change. Fetch before comparing remote refs when network access is available; report when it is unavailable.

## Publication sequence

1. Complete the Change review from `VERIFICATION.md`.
2. Commit verified branch work and push the Change branch automatically.
3. Wait for the user's final completion confirmation.
4. Update status and archive the Change, then commit.
5. Switch to an up-to-date clean `main` and merge with `--no-ff`.
6. Recheck the merged state, create annotated tag `change/YYYY-MM-DD-<name>`, and push `main` plus the tag.
7. Delete the merged Change branch locally and remotely. Keep unmerged alternatives.

Retry a failed step only after inspecting current local and remote state. All steps must be safe to repeat without duplicate archives, tags, or notifications.

If the target archive, branch, or tag name already exists with different content, stop and ask the user. Never overwrite it.

## Conflicts and divergence

- Report every text, tree, Spec, status, or remote-divergence conflict to the user.
- Do not resolve even an apparently simple conflict without the user's decision.
- Do not commit, merge, or push while a conflict is unresolved.
- Never fall back to reset, destructive checkout, history rewriting, rebase, or force push.

## Recovery and branching

Return to an earlier completion point by creating a new branch from its annotated tag. Preserve every existing branch and commit. Do not move an existing branch backward.

## Local Project Flow

`project/PROJECT_FLOW.md` is ignored and derived, never authoritative. Rebuild it from:

- `refs/heads/*`
- `refs/remotes/origin/*`, excluding symbolic `origin/HEAD`
- `refs/tags/change/*`

Use commit parent relationships, sanitized ref names, and at most the latest 200 relevant commits. Show active Changes, completed tags, forks, and merges as Mermaid plus normal Markdown links. Sort ties by commit time and full ref name. A repository with no commits gets an empty-start diagram. Refresh at session start and after branch, tag, merge, fetch, or push changes.
