# Handoff

## Objective

Separate AIPF development in `dev/` from the shipped product in `template/`, remove the development README, and implement/document template-only release publication.

## Git State

- Branch: `change/dev-template-separation`.
- Base and current HEAD before implementation commit: `9511de694104bd8cc31eaf9815d90828d7651a54`.
- Last fetch: origin/main matched main; origin/release matched local release (`d7dd6d5`).
- Changes: root routing and ignore rules modified; previous root management folders moved into dev/template; README moved to template; dev/template are new until staging. All changes belong to this Change; no unrelated dirty or staged files were present at start.
- No main merge, completion tag, or actual release update has been performed.

## Current State

Plan and Change attack/defense reviews completed. The main agent verified and accepted the revised result as pass. The user explicitly approved the proposed split and requested implementation; final completion confirmation has not been given. Development/product directories, routing, Spec/Status separation, product-only README, publication instructions, release script, and isolated tests are implemented. Commit and Change branch push remain before the final report.

## Verified Results

- `bash -n dev/scripts/update_release_branch.sh dev/tests/test_release.sh`: passed.
- `bash dev/tests/test_release.sh`: temporary repositories verified first publication, exact tree/manifest equality, dotfiles, no development data, legacy history preservation, no-op runs, wrong branch/detached/dirty/worktree rejection, unpublished-main rejection, push/retry, remote race and divergence.
- Structural Python check: canonical paths, only template README, relative Markdown links, byte-identical moved archive, ignored dev/template Flows, blank product Spec and lifecycle spaces passed.
- `git diff --check`: passed before staging.
- `git diff --cached --check`: passed after staging; only `template/README.md` is tracked as README, and no Flow is tracked.
- Missing product file and concurrent local release-ref updates: added to the suite and passed. The first local-ref race fixture did not change the product tree, so it correctly triggered no update; the fixture was corrected to create a new product snapshot before injecting the competing write.
- Final review corrections: reserved dev/nested-template paths, extra README, and required-file directory/symlink replacements are rejected; all added regression cases passed.
- Final attack/defense decisions are recorded in CHANGE.md. No unresolved findings remain.

## Failed Attempts

- Initial sandboxed `git fetch origin` could not write `.git/FETCH_HEAD`; escalated fetch succeeded. Git metadata writes require the permitted escalation.
- First combined delete/add apply_patch rejected duplicate targets before any edit; files were then written without that invalid patch form.

## Open Issues

- Existing release still contains the old Python CLI. Actual release publication is intentionally after the user's final completion confirmation and main merge/push.
- Verified Change branch commit/push remain before the user's final completion check.

## Next Action

Commit and push the reviewed Change branch, then request the user's final completion confirmation. After confirmation follow dev/instructions/END_CHANGE.md, GIT.md, and RELEASE.md to archive, merge/tag/push main, generate/push release, clean up the merged branch, and notify.

## Relevant Files

- `AGENTS.md`, `MEMORY_MAP.md`
- `dev/project/PROJECT_SPEC.md`, `dev/project/PROJECT_STATUS.md`
- `dev/change/dev-template-separation/CHANGE.md`
- `dev/instructions/GIT.md`, `dev/instructions/RELEASE.md`, `dev/instructions/END_CHANGE.md`
- `dev/scripts/update_release_branch.sh`, `dev/tests/test_release.sh`
- `template/AGENTS.md`, `template/MEMORY_MAP.md`, `template/README.md`, `template/project/`
