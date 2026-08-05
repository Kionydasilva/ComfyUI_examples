#!/bin/bash
# SessionStart hook: make the dev-browser skill usable in Claude Code on the web.
#
# This repo is documentation and example workflows, so there are no project
# dependencies to install. What does not survive a fresh container is the
# dev-browser CLI, so install it here and put the dev-browser-here wrapper on PATH.

set -euo pipefail

# Local machines already have their own setup; only bootstrap the remote container.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

if ! command -v dev-browser >/dev/null 2>&1; then
  echo "Installing dev-browser CLI..."
  npm install -g dev-browser
fi

# `dev-browser install` does two things: it unpacks the daemon's node_modules,
# then downloads Chrome for Testing. The download always fails here because the
# network allowlist rejects cdn.playwright.dev with a 403, but the daemon deps
# are already on disk by then, and those are required even when attaching over
# CDP. So run it, ignore the expected failure, and check what actually matters.
if [ ! -d "$HOME/.dev-browser/node_modules" ]; then
  echo "Priming dev-browser daemon (the browser download is expected to fail)..."
  dev-browser install >/dev/null 2>&1 || true
fi

if [ ! -d "$HOME/.dev-browser/node_modules" ]; then
  echo "dev-browser daemon dependencies missing after install; browser automation will not work." >&2
  exit 1
fi

chmod +x "$PROJECT_DIR/.claude/scripts/dev-browser-here" 2>/dev/null || true

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export PATH=\"$PROJECT_DIR/.claude/scripts:\$PATH\"" >> "$CLAUDE_ENV_FILE"
fi

echo "dev-browser ready. Use: dev-browser-here <<'EOF' ... EOF"
