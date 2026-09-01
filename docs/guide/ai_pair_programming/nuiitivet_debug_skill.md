# The `nuiitivet-debug` skill

`nuiitivet-debug` is an **AI skill** — a bundle of instructions you install into
your assistant so it can *run, hot-reload, inspect, and drive* a running Nuiitivet
app. It covers the see → act → verify leg of the
[AI pair-programming](index.md) loop, and is the companion to
[`nuiitivet-app`](nuiitivet_app_skill.md), which handles the *authoring* leg.

The tools it teaches are documented on their own pages —
[Hot Reload](hot_reload.md) and [Dev Bridge MCP](dev_bridge_mcp.md). This page is
about the skill: what it is, how to install it, and which judgement calls it
front-loads so the assistant does not have to rediscover them each session.

## Why it exists

Writing correct widget code is only half of pair-programming; the other half is
observing and driving the app that code produces. Left to itself an assistant
reaches for expensive `screenshot` calls, races spinners instead of waiting for
state to settle, or loses hot reload by passing an already-built root. This skill
front-loads the cheap, reliable way to work the running app.

## Install

Like `nuiitivet-app`, the skill lives in the Nuiitivet repository at
[`skills/nuiitivet-debug/`](https://github.com/yuksblog/nuiitivet/tree/main/skills/nuiitivet-debug) and follows the
**Agent Skills** open standard (a `SKILL.md`). It installs the same three ways
— see the [`nuiitivet-app` install section](nuiitivet_app_skill.md#install)
and substitute `nuiitivet-debug` for the skill name. The Claude Code plugin
installs both skills at once, and so does running
`python -m nuiitivet.skills install` without a skill name.

Once installed, the assistant loads this one whenever there is a Nuiitivet app to
run, verify, or debug — no per-session setup.

## What it front-loads

`SKILL.md` is organised as the loop itself — a one-time **Setup**, then
**Edit / See / Act / Verify**. Each section settles a judgement call the
assistant would otherwise get wrong:

- **Setup — the factory contract.** Launching with the dev runner and registering
  the bridge, plus the rule that keeps reload working: pass
  `App(Window(content=build_root))`, never `App(Window(content=build_root()))`, and put per-tree
  init in the factory or `__init__`, not `main()`. A stray call is the first thing
  to suspect when reload seems inert. → [Hot Reload](hot_reload.md)
- **See — choose the tool by question, not by habit.** `status` answers "is it
  up?", `describe_tree` "is the tree as intended?", `describe_state` "is the state
  as intended?" — between them, almost everything about your own change. Left to
  itself an assistant reaches for `screenshot`, which costs image tokens and
  usually shows less; the skill makes it the last resort even for a reported
  *visual* bug, where the cause is normally in the tree or the state.
- **See — the blind spots.** An action that appeared to do nothing is usually a
  handler that raised and was swallowed, which only `runtime_log` reveals — not
  another screenshot. Edits and clicks *you* made between turns live in
  `reload_log` and `interaction_log`.
- **Act — settle before observing.** `click` / `scroll` / `type` / `key`, then
  `wait_for` instead of an immediate `describe_tree` that races async work, with
  distinct patterns for waiting on async work versus on a *human*. Also which
  target a `scroll` takes — the scroll region, never a row inside it — and when
  `scroll_into_view` replaces it outright. → [Dev Bridge MCP](dev_bridge_mcp.md)
- **`key=` targeting.** Give a widget a stable `key` in its constructor so the
  bridge can drive it by name and its state survives a reorder across reloads.

The result is the loop **edit (hot reload) → see → act → verify → edit**.

## See also

- [AI pair-programming](index.md) — the loop this skill completes.
- [The `nuiitivet-app` skill](nuiitivet_app_skill.md) — the authoring companion.
- [Hot Reload](hot_reload.md) — the factory contract in depth.
- [Dev Bridge MCP](dev_bridge_mcp.md) — the bridge and its tools in depth.
