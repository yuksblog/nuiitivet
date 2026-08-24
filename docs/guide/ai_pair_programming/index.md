# AI pair-programming

Nuiitivet ships a modern development loop built for pairing with an AI
assistant: you and the assistant work on the same running window. You watch its
edits and screen actions land in real time, you can edit and manually test the
app yourself in the same session, and the assistant can see what *you* did
between its turns — so you stay on the same page.

<!-- TODO(#387): embed a short screencast of a pair-programming session here — a
     video conveys the loop far better than prose. Deferred until one is recorded. -->

## The two layers

This workflow assumes you already work in an AI programming environment — an
assistant like Claude Code or GitHub Copilot. Nuiitivet plugs into it on two
levels, and the rest of this section is organised the same way.

### Development-time features — what the framework provides

Set these up in your project. They are ordinary development tooling and work
whether or not an assistant is involved.

- **[Hot Reload](hot_reload.md)** — *write.* Launch your app with the dev runner
  (`python -m nuiitivet.dev run path/to/app.py`) so every save rebuilds the running
  window in place, with your `Observable` state and VSCode **F5** debug session
  intact.
- **[Dev Bridge MCP](dev_bridge_mcp.md)** — *see and act.* A localhost server the
  dev runner starts alongside hot reload, exposing the running app as MCP tools:
  read the widget tree, screenshot it, click and type, and pull your
  reload/interaction logs.

### AI skills — what the assistant is told about them

A skill is a bundle of instructions you copy into your assistant's skills
directory. The features above are usable without them; the skills are what make
an assistant reach for the right one at the right time instead of guessing.
Install either or both.

- **[The `nuiitivet-app` skill](nuiitivet_app_skill.md)** — *idioms.* Keeps the
  assistant's edits idiomatic Nuiitivet rather than leaking Flutter/React/Rx
  habits.
- **[The `nuiitivet-debug` skill](nuiitivet_debug_skill.md)** — *run and drive.*
  Teaches the assistant to launch under hot reload and work the dev bridge
  cheaply — check the tree before spending a screenshot, wait for async work
  instead of racing it.

## Which page answers what

| If you want to know… | Read |
| --- | --- |
| How do I get my app rebuilding on save, with state and breakpoints intact? | [Hot Reload](hot_reload.md) |
| What exactly can an assistant see and do in my running app? | [Dev Bridge MCP](dev_bridge_mcp.md) |
| How do I stop the assistant writing Flutter-flavoured Python? | [The `nuiitivet-app` skill](nuiitivet_app_skill.md) |
| How do I get the assistant to run and debug the app itself? | [The `nuiitivet-debug` skill](nuiitivet_debug_skill.md) |

The two feature pages are the reference for *what the tool does*; the two skill
pages cover *what the assistant is told about it*, and link back rather than
restate.
