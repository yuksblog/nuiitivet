# Install the skills

```bash
python -m nuiitivet.skills install
```

That installs all three skills into the current project. A skill is a bundle of
instructions your assistant loads on its own when the task calls for it; the
features of this section work without them, and the skills are what make the
assistant use them well. Install all three.

Each assistant reads its skills from its own directory. The default destination
is Claude's, `.claude/skills/`; for another assistant, pass its directory with
`--dest`.

| Skill | What it does for you |
| --- | --- |
| `nuiitivet-app` | The assistant writes idiomatic Nuiitivet. The API *resembles* Flutter, SwiftUI / Compose and Rx, so left alone it writes valid Python with their habits — `setState`, `Padding` / `SizedBox` wrappers, `subscribe()` to push a value into a widget |
| `nuiitivet-debug` | The assistant runs your app under hot reload, reads the running tree, drives it, and checks its own change before it answers — instead of guessing from a screenshot or racing a spinner |
| `nuiitivet-see-comments` | `/nuiitivet-see-comments` in chat: the assistant reads the comments you [wrote on the app](on_screen_modes.md#write-instructions-on-the-app-comment-mode) and handles every one in a turn, answering by number: `comment 1: done` |

The skills follow the **Agent Skills** open standard (a `SKILL.md`, plus
references and scripts), so the same directories work across assistants — only
the destination differs.

## Install from the package

The package carries the skills, so what it installs always matches the
nuiitivet version you have: re-run it after upgrading.

```bash
# project-local (default) — for Claude, .claude/skills/
python -m nuiitivet.skills install

# personal (available in every project) — for Claude, ~/.claude/skills/
python -m nuiitivet.skills install --user

# another assistant's skills directory — e.g. GitHub Copilot
python -m nuiitivet.skills install --dest .github/skills
```

`python -m nuiitivet.skills list` prints the names; naming one after `install`
installs only that skill.

## Install through the Claude Code plugin

One command pair installs the three skills and registers the
[dev bridge](dev_bridge_mcp.md) MCP server:

```text
/plugin marketplace add yuksblog/nuiitivet
/plugin install nuiitivet
```

## Copy them by hand

The skills live in the Nuiitivet repository under
[`skills/`](https://github.com/yuksblog/nuiitivet/tree/main/skills). From a
checkout, copy the three directories into your assistant's skills directory.
The examples use Claude's, `.claude/skills/`; for another assistant only the
destination changes, e.g. `.github/skills/` for GitHub Copilot:

```bash
cp -r path/to/nuiitivet/skills/nuiitivet-* .claude/skills/
```

Without a checkout, one at a time:

```bash
npx degit yuksblog/nuiitivet/skills/nuiitivet-app .claude/skills/nuiitivet-app
```

## Next Steps

- [Hot Reload](hot_reload.md) — launch your app so every save rebuilds the
  running window.
- [AI pair-programming](index.md) — the section overview.
