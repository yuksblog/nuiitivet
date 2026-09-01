#!/bin/sh
# Launch the nuiitivet dev-bridge MCP server from the Claude Code plugin.
#
# The plugin cannot pin a Python path the way a personal settings file can, so
# resolve one against the user's project, most specific first:
#   1. the project's .venv (pip and uv projects alike)
#   2. `uv run` on a uv-managed project (creates/syncs the env if needed)
#   3. plain `python` from PATH (an activated environment)
set -eu

dir="${CLAUDE_PROJECT_DIR:-$PWD}"

if [ -x "$dir/.venv/bin/python" ]; then
    exec "$dir/.venv/bin/python" -m nuiitivet.dev mcp
fi
if [ -x "$dir/.venv/Scripts/python.exe" ]; then
    exec "$dir/.venv/Scripts/python.exe" -m nuiitivet.dev mcp
fi
if [ -f "$dir/pyproject.toml" ] && command -v uv >/dev/null 2>&1; then
    cd "$dir"
    exec uv run python -m nuiitivet.dev mcp
fi
exec python -m nuiitivet.dev mcp
