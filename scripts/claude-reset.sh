#!/bin/bash
# Reset working directory to last commit
# Use this to recover from failed Claude Code operations

set -e

echo "Resetting working directory..."

# Discard all changes to tracked files
git checkout .

# Remove untracked files and directories
git clean -fd

echo "Done. Working directory restored to last commit."
echo "Current status:"
git status --short
