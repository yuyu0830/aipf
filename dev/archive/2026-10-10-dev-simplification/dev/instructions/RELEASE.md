# Release Publication

This instruction applies only to AIPF development. AIPF is a solo local project; keep publication to the required Git operations.

## Source and result

- `main` is the development source. `template/` contains the product files.
- Generate `release` from main's committed template content, placed at the release root. Do not edit release directly or copy the development repository wholesale.
- The script creates a local release commit and uses the existing local release as its parent, preserving previous publication history. Each invocation adds a publication commit.
- The only source README is `template/README.md`; it becomes release's `README.md`.

## Publication

1. Review, commit, and push the Change branch; obtain the user's final completion confirmation under `dev/instructions/END_CHANGE.md`.
2. Archive the Change, merge to main, and publish main and its completion tag under `dev/instructions/GIT.md`.
3. From the completed main checkout, generate and publish release:

```bash
bash dev/scripts/update_release_branch.sh
git push origin release
```

4. Refresh the ignored development Flow and finish Change branch cleanup and notification under END_CHANGE.

The script has no options and performs no fetch or push. It reads committed main rather than working-file edits. Ordinary Git errors stop execution; inspect the reported error before retrying. Do not force push or rewrite previous release history.

## Verification size

Use `bash -n dev/scripts/update_release_branch.sh` and a direct normal-path run in a temporary local repository when the script changes. There is no separate integrity checker, remote synchronization layer, race detector, or standing failure-case test suite. Add handling only after a concrete need arises.
