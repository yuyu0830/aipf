#!/usr/bin/env bash
# Publish the committed template tree without checking out or rewriting release.
set -euo pipefail

mode="${1:-local}"
if [[ $# -gt 1 || ! "$mode" =~ ^(local|--check|--push)$ ]]; then
  echo "usage: bash dev/scripts/update_release_branch.sh [--check|--push]" >&2
  exit 2
fi

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"
if [[ "$(git symbolic-ref --quiet --short HEAD || true)" != main ]]; then
  echo "error: run from main after Change completion and publication" >&2
  exit 2
fi
if [[ -n "$(GIT_OPTIONAL_LOCKS=0 git status --porcelain)" ]]; then
  echo "error: main must have no staged, unstaged, or untracked changes" >&2
  exit 2
fi
while IFS= read -r line; do
  if [[ "$line" == 'branch refs/heads/release' ]]; then
    echo "error: release is checked out in another worktree; leave it before publication" >&2
    exit 2
  fi
done < <(git worktree list --porcelain)

source_commit="$(git rev-parse HEAD)"
template_tree="$(git rev-parse --verify "${source_commit}:template")"
if [[ "$(git cat-file -t "$template_tree")" != tree ]]; then
  echo "error: main:template must be a directory" >&2
  exit 2
fi
for path in .gitignore AGENTS.md MEMORY_MAP.md README.md project/PROJECT_SPEC.md \
  project/PROJECT_STATUS.md instructions/COMMON.md instructions/GIT.md src/CURRENT_VERSION; do
  file_type="$(git cat-file -t "${template_tree}:${path}" 2>/dev/null || true)"
  file_entry="$(git ls-tree "$template_tree" -- "$path")"
  if [[ "$file_type" != blob || ! "$file_entry" =~ ^100(644|755)[[:space:]]blob[[:space:]] ]]; then
    echo "error: required product file is missing or not a regular file: template/$path" >&2
    exit 2
  fi
done
while read -r file_mode _; do
  if [[ "$file_mode" == 160000 ]]; then
    echo "error: template must contain files, not submodules" >&2
    exit 2
  fi
done < <(git ls-tree -r "$template_tree")
while IFS= read -r -d '' product_path; do
  case "$product_path" in
    dev|dev/*|template|template/*)
      echo "error: development/nested template path is forbidden in product: $product_path" >&2
      exit 2 ;;
    */README.md)
      echo "error: the product must have only its root README.md: $product_path" >&2
      exit 2 ;;
  esac
done < <(git ls-tree -rz --name-only "$template_tree")

remote_main=""
remote_release=""
if git remote get-url origin >/dev/null 2>&1; then
  if [[ "$mode" == --check ]]; then
    # Query the server without changing FETCH_HEAD, objects, or tracking refs.
    remote_refs="$(git ls-remote --heads origin refs/heads/main refs/heads/release)"
    while read -r sha ref; do
      case "$ref" in
        refs/heads/main) remote_main="$sha" ;;
        refs/heads/release) remote_release="$sha" ;;
      esac
    done <<< "$remote_refs"
  else
    git fetch --prune origin
    remote_main="$(git rev-parse --verify --quiet refs/remotes/origin/main || true)"
    remote_release="$(git rev-parse --verify --quiet refs/remotes/origin/release || true)"
  fi
  if [[ "$remote_main" != "$source_commit" ]]; then
    echo "error: main=$source_commit differs from origin/main=${remote_main:-absent}; reconcile before retrying" >&2
    exit 2
  fi
elif [[ "$mode" == --push ]]; then
  echo "error: --push requires origin; no release ref was changed" >&2
  exit 2
fi

local_release="$(git rev-parse --verify --quiet refs/heads/release || true)"
parent="$local_release"
if [[ -n "$remote_release" ]]; then
  if ! git cat-file -e "${remote_release}^{commit}" 2>/dev/null; then
    echo "error: remote release=$remote_release is not available locally; fetch origin, then retry --check" >&2
    exit 2
  fi
  if [[ -z "$local_release" ]] || git merge-base --is-ancestor "$local_release" "$remote_release"; then
    parent="$remote_release"
  elif ! git merge-base --is-ancestor "$remote_release" "$local_release"; then
    echo "error: release=$local_release and origin/release=$remote_release diverged; user decision required" >&2
    exit 2
  fi
fi

parent_tree=""
if [[ -n "$parent" ]]; then
  parent_tree="$(git rev-parse "${parent}^{tree}")"
fi
if [[ "$mode" == --check ]]; then
  echo "source main: $source_commit"
  echo "template tree: $template_tree"
  echo "release parent: ${parent:-none (first publication)}"
  if [[ "$parent_tree" == "$template_tree" ]]; then
    echo "check passed: release already matches template; no commit needed"
  else
    echo "check passed: release would be generated from template; no changes made"
  fi
  exit 0
fi

# Recheck source and files after network operations, then condition the ref write
# on the release value we inspected. A competing ref update must fail visibly.
if [[ "$(git symbolic-ref --quiet --short HEAD || true)" != main || \
  "$(git rev-parse HEAD)" != "$source_commit" || -n "$(GIT_OPTIONAL_LOCKS=0 git status --porcelain)" ]]; then
  echo "error: main or its files changed during publication; inspect state before retrying" >&2
  exit 2
fi
release_commit="$parent"
if [[ "$parent_tree" != "$template_tree" ]]; then
  parents=()
  if [[ -n "$parent" ]]; then
    parents=(-p "$parent")
  fi
  release_commit="$(git commit-tree "$template_tree" "${parents[@]}" \
    -m "release: publish template from ${source_commit}")"
fi
if [[ "$release_commit" != "$local_release" ]]; then
  git update-ref -m "release: publish template from ${source_commit}" \
    refs/heads/release "$release_commit" "$local_release"
fi
if [[ "$(git rev-parse "${release_commit}^{tree}")" != "$template_tree" ]]; then
  echo "error: release tree mismatch; publication stopped" >&2
  exit 2
fi
echo "release: $release_commit (source main: $source_commit)"
if [[ "$mode" == --push ]]; then
  if ! git push origin "${release_commit}:refs/heads/release"; then
    echo "error: push failed; local release=$release_commit is preserved. Fetch and inspect origin/release before retrying; never force push." >&2
    exit 1
  fi
  echo "published release; refresh dev/project/PROJECT_FLOW.md"
else
  echo "local release prepared; run with --push to publish, then refresh dev/project/PROJECT_FLOW.md"
fi
