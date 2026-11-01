#!/usr/bin/env bash
# Install the pre-commit hook into this clone's shared hooks directory, so it covers
# the main checkout and every worktree. Copies rather than symlinks: a symlink into a
# worktree breaks when that worktree is removed. Rerun after editing the hook.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
hooks="$(git rev-parse --path-format=absolute --git-common-dir)/hooks"
if [ -e "$hooks/pre-commit" ] && ! cmp -s "$here/pre-commit" "$hooks/pre-commit"; then
    echo "error: $hooks/pre-commit exists and differs; merge it by hand" >&2
    exit 1
fi
install -m 0755 "$here/pre-commit" "$hooks/pre-commit"
echo "installed $hooks/pre-commit"
