# Agent skills for Nuiitivet users

This directory holds **published skills** for AI coding assistants (Claude Code,
and compatible agents) that build applications *with* Nuiitivet. They are shipped
in the repository — unlike the maintainers' local `.claude/` tooling, which is
git-ignored — so framework users can adopt them.

> Not to be confused with `.claude/` / `.github/skills/`, which are the Nuiitivet
> *maintainers'* development tools and are intentionally untracked.

## Available skills

| Skill | Purpose |
| --- | --- |
| [`nuiitivet-app/`](nuiitivet-app/) | Build, edit, and review Nuiitivet apps with the correct idioms (Observable state, modifiers, Navigator/Overlay), plus a linter that flags leaked Flutter/React/Rx patterns. |

## How to use a skill

**Claude Code** — copy the skill into your project's skills directory so the
agent discovers it automatically:

```
cp -r skills/nuiitivet-app <your-project>/.claude/skills/nuiitivet-app
```

The agent loads `SKILL.md`, follows the referenced material in `references/`, and
runs the bundled linter as the final step:

```
python .claude/skills/nuiitivet-app/scripts/check_idioms.py <files-or-dirs>
```

**Any assistant / manual use** — point the assistant at
[`nuiitivet-app/SKILL.md`](nuiitivet-app/SKILL.md); it stands alone as a written
guide, and the linter runs as an ordinary Python script with no dependencies:

```
python skills/nuiitivet-app/scripts/check_idioms.py <files-or-dirs>
```
