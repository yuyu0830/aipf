#!/usr/bin/env bash
# Build a local release from main's committed template. Push separately.
set -e

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"
source_commit="$(git rev-parse main)"
template_tree="$(git rev-parse "${source_commit}:template")"

parents=()
if git show-ref --verify --quiet refs/heads/release; then
  parents=(-p "$(git rev-parse release)")
fi
release_commit="$(git commit-tree "$template_tree" "${parents[@]}" \
  -m "release: publish template from ${source_commit}")"
git update-ref refs/heads/release "$release_commit"
echo "local release: $release_commit (source main: $source_commit)"
