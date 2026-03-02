#!/usr/bin/env bash
set -euo pipefail

# Remove from index only files that are BOTH tracked and ignored by current rules.
# Keeps local files on disk.
tracked_ignored=$(git ls-files -ci --exclude-standard)

if [[ -z "$tracked_ignored" ]]; then
  echo "No tracked ignored files found."
  exit 0
fi

echo "Removing tracked ignored files from index:"
echo "$tracked_ignored"

git ls-files -ci --exclude-standard -z | xargs -0 git rm --cached --ignore-unmatch

echo
echo "Done. Review and commit:"
echo "  git status --short"
echo "  git commit -m 'Stop tracking ignored files'"