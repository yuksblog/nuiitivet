"""Sanity checks for the Claude Code plugin manifests in .claude-plugin/."""

from __future__ import annotations

import json
from importlib import metadata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = REPO_ROOT / ".claude-plugin"


def _load(name: str) -> dict:
    with open(PLUGIN_DIR / name, encoding="utf-8") as handle:
        payload = json.load(handle)
    assert isinstance(payload, dict)
    return payload


def test_marketplace_lists_the_root_plugin() -> None:
    marketplace = _load("marketplace.json")
    assert marketplace["name"] == "nuiitivet"
    assert marketplace["owner"]["name"]
    (entry,) = marketplace["plugins"]
    assert entry["name"] == "nuiitivet"
    assert entry["source"] == "."


def test_plugin_manifest_matches_the_package() -> None:
    plugin = _load("plugin.json")
    assert plugin["name"] == "nuiitivet"
    # The plugin version is bumped alongside the package version on release.
    assert plugin["version"] == metadata.version("nuiitivet")


def test_plugin_bundles_the_dev_bridge_server() -> None:
    plugin = _load("plugin.json")
    server = plugin["mcpServers"]["nuiitivet-dev"]
    assert server["command"] == "sh"
    # The launcher resolves a Python for the user's project (.venv, uv, PATH).
    (script,) = server["args"]
    assert script == "${CLAUDE_PLUGIN_ROOT}/scripts/dev/plugin_mcp_launcher.sh"
    launcher = REPO_ROOT / "scripts" / "dev" / "plugin_mcp_launcher.sh"
    assert launcher.is_file()
    assert launcher.stat().st_mode & 0o111, "launcher must be executable"


def test_plugin_skills_are_discoverable() -> None:
    # Plugins auto-discover skills from <plugin-root>/skills/; every entry
    # shipped there must be a real skill.
    skills = [p for p in (REPO_ROOT / "skills").iterdir() if p.is_dir()]
    names = {p.name for p in skills}
    assert {"nuiitivet-app", "nuiitivet-debug"} <= names
    for skill in skills:
        assert (skill / "SKILL.md").is_file(), f"{skill.name} lacks SKILL.md"
