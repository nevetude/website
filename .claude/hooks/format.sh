#!/usr/bin/env bash
# Formats the file Claude just edited. Silent no-op until the toolchains exist.
f=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))')
[ -f "$f" ] || exit 0
export PATH="$HOME/.local/share/fnm:$HOME/.local/bin:$PATH"
command -v fnm >/dev/null && eval "$(fnm env --shell bash)"
cd "$CLAUDE_PROJECT_DIR" || exit 0

case "$f" in
  */backend/*.py)
    [ -f backend/pyproject.toml ] && (cd backend && uv run --quiet ruff format "$f" && uv run --quiet ruff check --fix --quiet "$f") >/dev/null 2>&1
    ;;
  */frontend/*.ts|*/frontend/*.svelte|*/frontend/*.css)
    [ -d frontend/node_modules ] && (cd frontend && pnpm exec prettier --write "$f") >/dev/null 2>&1
    ;;
esac
exit 0
