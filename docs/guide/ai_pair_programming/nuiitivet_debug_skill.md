# The `nuiitivet-debug` skill

`nuiitivet-debug` is an **AI skill** — a bundle of instructions you install into
your assistant so it can *run, hot-reload, inspect, and drive* a running Nuiitivet
app. It is the see → act → verify leg of the
[AI pair-programming](index.md) loop, and the companion to
[`nuiitivet-app`](nuiitivet_app_skill.md), which handles the *authoring* leg.

## Why it exists

Writing correct widget code is only half of pair-programming; the other half is
observing and driving the app that code produces. Left to itself an assistant
reaches for expensive `screenshot` calls, races spinners instead of waiting for
state to settle, or loses hot reload by passing an already-built root. This skill
front-loads the cheap, reliable way to work the running app.

## Install

The skill lives in the Nuiitivet repository at
[`skills/nuiitivet-debug/`](../../../skills/nuiitivet-debug/). Like
`nuiitivet-app`, it is **not** part of the pip package — copy the directory into
your assistant's skills directory. It follows the **Agent Skills** open standard
(a `SKILL.md`), so the same directory works across assistants; only the
destination differs.

### Claude Code

```bash
# project-local (checked in with your repo)
cp -r path/to/nuiitivet/skills/nuiitivet-debug .claude/skills/nuiitivet-debug

# or personal (available in every project)
cp -r path/to/nuiitivet/skills/nuiitivet-debug ~/.claude/skills/nuiitivet-debug
```

### GitHub Copilot

```bash
# project-local (checked in with your repo)
cp -r path/to/nuiitivet/skills/nuiitivet-debug .github/skills/nuiitivet-debug

# or personal (available in every project)
cp -r path/to/nuiitivet/skills/nuiitivet-debug ~/.copilot/skills/nuiitivet-debug
```

`nuiitivet-app` and `nuiitivet-debug` are independent — install either or both.

## What it front-loads

- **Launching under hot reload** — `python -m nuiitivet.dev path/to/app.py`, and
  the **factory contract** that keeps reload working (core rule 6: pass
  `App(content=build_root)`, never `App(content=build_root())`; per-tree init in
  the factory / `__init__`, not `main()`).
- **The dev bridge / MCP server** — register once with
  `python -m nuiitivet.dev mcp` (needs `pip install 'nuiitivet[mcp]'`), then check
  and drive the live app.
- **Checking — by question, not as a sequence** — `status` (is it up?),
  `describe_tree` (is the tree as intended?), and `describe_state` (is the state
  as intended?) answer almost everything about your own changes. `runtime_log`
  explains an action that seemed to do nothing (a swallowed handler exception);
  `reload_log` and `interaction_log` catch edits and clicks the human made between
  turns. `screenshot` is the genuine last resort — even for a reported visual
  problem, confirm the tree and state first; the cause is usually there, not the
  pixels.
- **Acting and settling** — `click` / `type` / `key`, then `wait_for` to observe
  the settled state instead of racing async work, with a distinct pattern for
  waiting on a *human* versus on async work.
- **`keyed()` targeting** — attach a stable `key` so the bridge can drive a widget
  by name and its state survives a reorder across reloads.

The result is the loop **edit (hot reload) → see → act → verify → edit**.

## See also

- [AI pair-programming](index.md) — the loop this skill completes.
- [The `nuiitivet-app` skill](nuiitivet_app_skill.md) — the authoring companion.
- [Hot Reload](hot_reload.md) — the factory contract in depth.
- [Dev Bridge MCP](dev_bridge_mcp.md) — the bridge and its tools in depth.
