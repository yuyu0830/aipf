#!/usr/bin/env bash
set -euo pipefail

source_ref="${1:-main}"
release_branch="${2:-release}"

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "error: commit or stash working-tree changes before updating the release branch" >&2
  exit 2
fi

if ! git rev-parse --verify --quiet "${source_ref}^{commit}" >/dev/null; then
  echo "error: source ref does not exist: $source_ref" >&2
  exit 2
fi

source_commit="$(git rev-parse "${source_ref}^{commit}")"
release_worktree="$(mktemp -d "${TMPDIR:-/tmp}/aipf-release.XXXXXX")"

cleanup() {
  git worktree remove --force "$release_worktree" >/dev/null 2>&1 || true
  rm -rf -- "$release_worktree"
}
trap cleanup EXIT

if git show-ref --verify --quiet "refs/heads/$release_branch"; then
  git worktree add --detach "$release_worktree" "$release_branch" >/dev/null
else
  git worktree add --detach "$release_worktree" "$source_commit" >/dev/null
  git -C "$release_worktree" switch --orphan "$release_branch" >/dev/null
fi

git -C "$release_worktree" rm -rf --ignore-unmatch . >/dev/null
git archive "$source_commit" \
  dev/pyproject.toml \
  dev/src \
  dev/RELEASE_README.md \
  dev/RELEASE.gitignore \
  | tar -x -C "$release_worktree"

mv "$release_worktree/dev/pyproject.toml" "$release_worktree/pyproject.toml"
mv "$release_worktree/dev/src" "$release_worktree/src"
mv "$release_worktree/dev/RELEASE_README.md" "$release_worktree/README.md"
mv "$release_worktree/dev/RELEASE.gitignore" "$release_worktree/.gitignore"
rmdir "$release_worktree/dev"

git -C "$release_worktree" add --all
if git -C "$release_worktree" diff --cached --quiet; then
  echo "release branch already matches $source_commit"
  exit 0
fi

git -C "$release_worktree" commit \
  -m "release: publish from ${source_commit}" >/dev/null

release_commit="$(git -C "$release_worktree" rev-parse HEAD)"
git -C "$release_worktree" switch --detach >/dev/null
git branch --force "$release_branch" "$release_commit" >/dev/null
echo "updated $release_branch to $release_commit from $source_commit"
echo "push with: git push origin $release_branch"
