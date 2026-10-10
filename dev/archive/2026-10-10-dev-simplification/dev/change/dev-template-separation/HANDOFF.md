# Handoff

## Objective

Keep AIPF development under dev and the product under template, with only the product README. Per the latest user instruction, keep AIPF's solo local implementation minimal and remove integrity/overly defensive code.

## Git State

- Branch: `change/dev-template-separation`.
- Original Change base: `9511de694104bd8cc31eaf9815d90828d7651a54`.
- Last published HEAD before this simplification: `f11efd91ffad156a0e307b72c68701c9761e1fd4`.
- Latest fetch confirmed origin/main and origin/release unchanged from the previous session. The Change branch was clean and matched its upstream before these edits.
- This commit contains only owned simplification changes: development routing/rules/Spec/Status, current Change/Handoff, release script, deletion of test_release.sh, and the previous Spec copy in dev/project/old/PROJECT_SPEC_001.md.
- Check current HEAD/upstream with Git at resume. Main, release, and completion tags have not been updated by this Change.

## Current State

The original directory separation is retained. The 150-line release script is reduced to 17 lines: read committed main:template, create a release commit with the existing local release as parent if present, and update the local ref. Push is a separate normal Git command. The 227-line defensive test script is removed. The product template is unchanged by this simplification.

Root and dev instructions now require minimum implementation for AIPF's solo local use, direct tool failures and proportional checks, adding guards/tests only for an actual need. Product projects keep their independent requirements. The previous development Spec was preserved before updating it.

## Verified Results

- `bash -n dev/scripts/update_release_branch.sh`: passed.
- A direct normal-path run in a temporary local Git repository: first release contained root .gitignore and README without the development file; next product update retained the earlier release as parent. Temporary repository removed.
- `git diff --check`: passed.
- `git diff --name-only -- template`: no output; product content unchanged this turn.
- Old --check/--push/test_release.sh references removed from current development routing and release instructions. Historical verification remains in Git and is marked as superseded in CHANGE.md.
- Focused revised Plan and final source review: simplify_plan_attack and simplify_defend both passed with no findings. The main agent checked the source, documents and direct execution evidence and accepted pass; results are recorded in CHANGE.md.

## Failed Attempts

Removing the now-unused dev/tests directory failed because it contains ignored historical __pycache__ files. The owned tracked test script was deleted successfully; unrelated ignored cache files were left untouched. Do not retry broad directory removal.

## Open Issues

Final user completion confirmation remains pending. The real release still contains the old CLI and will change only after completion and main publication.

## Next Action

Publish the reviewed simplification commit with this Handoff and report it. Final completion confirmation remains pending. After confirmation follow dev/instructions/END_CHANGE.md and RELEASE.md for archive/main publication, local release generation, separate git push origin release, and cleanup.

## Relevant Files

- `AGENTS.md`, `dev/instructions/COMMON.md`, `dev/instructions/CODE_GENERATION.md`, `dev/instructions/VERIFICATION.md`
- `dev/project/PROJECT_SPEC.md`, `dev/project/PROJECT_STATUS.md`
- `dev/change/dev-template-separation/CHANGE.md`
- `dev/scripts/update_release_branch.sh`, `dev/instructions/RELEASE.md`, `dev/instructions/GIT.md`
