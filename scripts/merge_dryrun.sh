#!/usr/bin/env bash
# Dry-run merging every origin/<lane> branch, chained, onto origin/main.
# Uses `git merge-tree` + dangling commits: no branch, ref, index or worktree changes.
# Prints ok/CONFLICT per branch and the final commit, which you can inspect with
#   git worktree add --detach /tmp/dry <commit>
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

git fetch -q origin
cur="$(git rev-parse origin/main)"
for r in $(git for-each-ref --format='%(refname:short)' refs/remotes/origin); do
    case "$r" in origin/HEAD|origin/main|origin) continue ;; esac
    [ "$(git rev-list --count "$cur..$r")" = 0 ] && continue
    if out="$(git merge-tree --write-tree --name-only "$cur" "$r" 2>&1)"; then
        cur="$(git commit-tree "$(echo "$out" | head -1)" -p "$cur" -p "$r" -m "dry-run merge $r")"
        echo "ok       $r"
    else
        echo "CONFLICT $r: $(echo "$out" | sed -n '2,/^$/p' | grep -v '^$' | tr '\n' ' ')"
    fi
done
echo "integrated commit: $cur"
