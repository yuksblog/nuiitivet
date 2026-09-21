# Agent skills for Nuiitivet users

This directory holds **published skills** for coding agents (Claude Code and
compatible agents) that build applications *with* Nuiitivet. They are shipped
in the repository — unlike the maintainers' local `.claude/` tooling, which is
git-ignored — so framework users can adopt them.

> Not to be confused with `.claude/` / `.github/skills/`, which are the Nuiitivet
> *maintainers'* development tools and are intentionally untracked.

## Available skills

| Skill | Purpose |
| --- | --- |
| [`nuiitivet-app/`](nuiitivet-app/) | **Build** Nuiitivet apps with the correct idioms (Observable state, modifiers, Navigator/Overlay), plus a linter that flags leaked Flutter/React/Rx patterns. |
| [`nuiitivet-debug/`](nuiitivet-debug/) | **Run, hot-reload, inspect, and drive** a running app — the dev runner and the dev-bridge / MCP tools (`status`, `describe_tree`, `screenshot`, `click`, `scroll_into_view`, `wait_for`) for the see → act → verify loop. |
| [`nuiitivet-see-comments/`](nuiitivet-see-comments/) | **Read and act on the comments** the user left in the running app (comment mode): `/nuiitivet-see-comments`, or `see_comments` in chat. Falls back to the CLI when the MCP server is not registered. |

`nuiitivet-app` *writes* the code; `nuiitivet-debug` *runs and debugs* what was
written; `nuiitivet-see-comments` *acts on what the user pointed at*. They are
independent — install any of them.

## How to use a skill

**Claude Code** — copy the skill into your project's skills directory so the
agent discovers it automatically (copy each skill you want):

```
cp -r skills/nuiitivet-app          <your-project>/.claude/skills/nuiitivet-app
cp -r skills/nuiitivet-debug        <your-project>/.claude/skills/nuiitivet-debug
cp -r skills/nuiitivet-see-comments <your-project>/.claude/skills/nuiitivet-see-comments
```

The agent loads each `SKILL.md`, follows any referenced material in `references/`,
and — for `nuiitivet-app` — runs the bundled linter as the final step:

```
python .claude/skills/nuiitivet-app/scripts/check_idioms.py <files-or-dirs>
```

**Any agent / manual use** — point the agent at
[`nuiitivet-app/SKILL.md`](nuiitivet-app/SKILL.md); it stands alone as a written
guide, and the linter runs as an ordinary Python script with no dependencies:

```
python skills/nuiitivet-app/scripts/check_idioms.py <files-or-dirs>
```
