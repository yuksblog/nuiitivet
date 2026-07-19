# AI pair-programming

Nuiitivet ships a modern develop loop built for pairing with an AI assistant: you
and the assistant work on the same running window. You watch its edits and screen
actions land in real time, you can edit and manually test the app yourself in the
same session, and the assistant can see what *you* did between its turns — so you
stay on the same page.

<!-- TODO(#387): embed a short screencast of a pair-programming session here — a
     video conveys the loop far better than prose. Deferred until one is recorded. -->

## The three pieces

This workflow assumes you already work in an AI programming environment — an
assistant like Claude Code or GitHub Copilot. On top of that, three Nuiitivet
features plug into that environment; set up each one:

- **[Hot Reload](hot_reload.md)** — *write.* Launch your app with the dev runner
  (`python -m nuiitivet.dev path/to/app.py`) so every save rebuilds the running
  window in place, with your `Observable` state and VSCode **F5** debug session
  intact.
- **[Dev Bridge MCP](dev_bridge_mcp.md)** — *see and act.* Register the bridge as
  an MCP server in your assistant so it can read the running tree, screenshot it,
  click and type, and pull your reload/interaction logs to catch up on your turn.
- **[The `nuiitivet-app` skill](nuiitivet_app_skill.md)** — *idioms.* Install the
  skill into your assistant's skills directory so its edits stay idiomatic
  Nuiitivet rather than leaking Flutter/React/Rx habits.
