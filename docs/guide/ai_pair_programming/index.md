# AI pair-programming

A coding agent gets the first version of an app on screen quickly. What
follows is a back-and-forth, and it comes in two kinds:

- **Refine** — bringing what works closer to what you want.
- **Debug** — fixing what behaves wrong.

Both can be done through chat, and both are hard to put into prose. With
Nuiitivet you drag, mark and comment on the running app itself, and the agent
looks at the same window: it edits, drives the app, checks its own change, and
reads what *you* did between its turns. The conversation moves from the chat
to the app.

## Which page answers what

This workflow assumes you already work with a coding agent such as Claude Code
or GitHub Copilot. The pages follow the order you meet them in:

| If you want to… | Read |
| --- | --- |
| Get the agent writing idiomatic Nuiitivet, and running and checking the app itself | [Install the skills](install_skills.md) |
| Get your app rebuilding on save, with state and breakpoints intact | [Hot Reload](hot_reload.md) |
| Tell the agent what to change, or what went wrong, from the app's own screen — or fix the layout yourself | [The on-screen modes](on_screen_modes.md) |
| Know what the agent can see and do in your running app, and set that up | [Dev Bridge MCP](dev_bridge_mcp.md) |

Hot reload, the on-screen modes and the dev bridge are ordinary development
tooling the framework provides: they work whether or not an agent is
involved. The skills are what the agent is told about them.
