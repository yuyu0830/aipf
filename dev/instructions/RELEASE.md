# Release Publication

This instruction applies only to AIPF development. The released user's project has no AIPF release-generation workflow.

## Authority and source

- `main` contains AIPF development records and the product under `template/`.
- `release` is generated from the committed `template/` tree of an accepted, clean `main` revision. Never edit release directly.
- The release root tree ID must equal `main:template`. This includes dotfiles, executable modes, and all committed product files, without `dev/`, root development routers, or development archives.
- Development routers remain on main. The product has its own `AGENTS.md`, `MEMORY_MAP.md`, and the only README, `template/README.md`, which becomes release's `README.md`.
- Keep previous release commits as parents. The transition from the old Python CLI distribution removes the old files in a new commit; it never rewrites history.

## Completion and publication order

1. Review the Change under `dev/instructions/VERIFICATION.md`; commit and push the verified Change branch.
2. Wait for the user's final completion confirmation under `dev/instructions/END_CHANGE.md`. An implementation command does not replace this final check.
3. Update development Status, archive the Change, and commit. Fetch and inspect refs, merge to clean synchronized main with `--no-ff`, recheck, then tag and push main plus its completion tag under `dev/instructions/GIT.md`.
4. Run the structural checks and `bash dev/tests/test_release.sh`. These checks use temporary repositories and do not publish the real release.
5. From clean main equal to origin/main, inspect and publish:

```bash
bash dev/scripts/update_release_branch.sh --check
bash dev/scripts/update_release_branch.sh --push
```

6. Confirm `git rev-parse release^{tree}` equals `git rev-parse main:template`, and confirm origin/release points to the published release commit. Refresh ignored `dev/project/PROJECT_FLOW.md`.
7. Delete only the merged Change branch locally and remotely, then send the completion notification under END_CHANGE. Keep unmerged alternatives.

Record any failed step and exact refs in the archived Handoff before retrying. Earlier successful publication steps remain valid.

## Script modes

| Invocation | Behavior |
|---|---|
| `--check` | Read-only: check local state and query origin using ls-remote; no local files, refs, or objects change. Report whether a new release commit is needed. If remote objects are unavailable locally, ask the operator to fetch first. |
| No argument | Generate/update local release only. If origin exists, fetch/prune and require main==origin/main. Without origin this supports isolated local verification. |
| `--push` | Require origin, fetch/prune, require main==origin/main, update local release and perform a regular fast-forward push. |

All modes require clean main and required committed template files as regular blobs, not directories or symlinks. Reject reserved `dev/` or nested `template/` product paths, extra READMEs, template submodules, and a release checked out in another worktree. Only the product root README is allowed. These structural guards cannot identify arbitrary development text inside other files; reviewing template content remains part of the Change review. The script never switches branches or rewrites working files. It uses Git tree/commit objects and conditional `update-ref`.

On first publication without local or remote release, create a root commit containing only the template tree. If local and remote release are in a straight line, use the newer tip as parent; if they diverge, stop for the user's decision. When the parent tree already matches template, reuse its commit rather than adding an empty publication commit. The source main revision is recorded in every new publication commit message; no-op runs retain the original message.

## Failure and recovery

- Dirty main, missing product files, main/origin mismatch: stop before changing release. Inspect and complete or reconcile the pending work under GIT; never stash, reset, or overwrite someone else's work automatically.
- Release divergence: report both tips and wait for the user's decision. Never merge, rebase, reset, or force push release automatically.
- Release used by a worktree: stop. Inspect the worktree and leave release safely before retrying; never forcibly remove it.
- Conditional ref update failure: another writer moved release. Inspect refs; the generated but unreferenced commit does not authorize overwriting the new ref.
- Push failure or remote race: the prepared local commit remains. Fetch and inspect local/remote ancestry; rerun only after resolving any conflict. A straight-line unpublished local release can be pushed on retry without duplicate commits.
- A network failure is a failed publication, not permission to use stale remote refs. The read-only checker also fails if it cannot query origin.
- The script cannot lock the remote server. It checks main before preparing release; final publication uses ordinary fast-forward Git push. If main advances concurrently, the release remains a snapshot of its recorded accepted source and the next completed publication can update it.

Never copy the development repository wholesale into release. Never use a source/ref override, force push, or direct release edits as a shortcut.
