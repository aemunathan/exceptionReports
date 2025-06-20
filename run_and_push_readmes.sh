#!/bin/bash

# Adjust this to your base directory of repositories
BASE_DIR=~/java-projects
SCRIPT_PATH=generate_flexible_readmes_with_git.py

echo "Running README generator..."
python3 "$SCRIPT_PATH"

echo "Checking repositories for new README commits..."

for dir in "$BASE_DIR"/*/; do
  [ -d "$dir/.git" ] || continue
  cd "$dir"

  if git status --porcelain | grep -q README.md; then
    echo "Updating $(basename "$dir")..."
    git add README.md
    git commit -m "Auto-generated README.md"
    git push origin HEAD
  else
    echo "No README changes in $(basename "$dir")."
  fi
done

echo "✅ All done."
