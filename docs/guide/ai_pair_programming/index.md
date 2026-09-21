# AI pair-programming

Nuiitivet ships a modern development loop built for pairing with an AI
assistant: you and the assistant work on the same running window. You watch its
edits and screen actions land in real time, you can edit and manually test the
app yourself in the same session, and the assistant can see what *you* did
between its turns — so you stay on the same page.

<!-- TODO(#387): embed a short screencast of a pair-programming session here — a
     video conveys the loop far better than prose. Deferred until one is recorded. -->

## Which page answers what

This workflow assumes you already work with an AI assistant such as Claude Code
or GitHub Copilot. The pages follow the order you meet them in:

| If you want to… | Read |
| --- | --- |
| Get the assistant writing idiomatic Nuiitivet, and running and checking the app itself | [Install the skills](install_skills.md) |
| Get your app rebuilding on save, with state and breakpoints intact | [Hot Reload](hot_reload.md) |
| Tell the assistant what to change from the app's own screen, or fix the layout yourself | [The on-screen modes](on_screen_modes.md) |
| Know what the assistant can see and do in your running app, and set that up | [Dev Bridge MCP](dev_bridge_mcp.md) |

Hot reload, the on-screen modes and the dev bridge are ordinary development
tooling the framework provides: they work whether or not an assistant is
involved. The skills are what the assistant is told about them.
