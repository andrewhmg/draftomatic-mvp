#!/bin/zsh
# Install the Draftomatic pre-commit hook (run once after cloning)
cd "$(git rev-parse --show-toplevel)"
cp .githook/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit && echo "pre-commit hook installed (ruff gate)"
