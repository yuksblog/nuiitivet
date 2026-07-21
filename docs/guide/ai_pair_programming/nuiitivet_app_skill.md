# The `nuiitivet-app` skill

`nuiitivet-app` is an **AI skill** — a bundle of instructions you install into
your assistant so it writes idiomatic Nuiitivet code. It is the authoring leg of
the [AI pair-programming](index.md) loop.

## Why it exists

Nuiitivet's surface *resembles* Flutter (widgets), SwiftUI/Compose (modifiers),
and Rx/WPF (`Observable`), so an assistant readily writes valid Python that
follows those other frameworks' habits — `setState`, `SizedBox`/`Padding`
wrappers, `subscribe()` to push values — instead of Nuiitivet's idioms. The skill
front-loads the correct idioms and ships a linter that flags the leaks.

## Install

The skill lives in the Nuiitivet repository at
[`skills/nuiitivet-app/`](../../../skills/nuiitivet-app/). It is **not** part of
the pip package — you copy the directory into your assistant's skills directory.
It follows the **Agent Skills** open standard (a `SKILL.md` plus its references
and linter script), so the *same* directory works across assistants — only the
destination differs.

### Claude Code

```bash
# project-local (checked in with your repo)
cp -r path/to/nuiitivet/skills/nuiitivet-app .claude/skills/nuiitivet-app

# or personal (available in every project)
cp -r path/to/nuiitivet/skills/nuiitivet-app ~/.claude/skills/nuiitivet-app
```

### GitHub Copilot

```bash
# project-local (checked in with your repo)
cp -r path/to/nuiitivet/skills/nuiitivet-app .github/skills/nuiitivet-app

# or personal (available in every project)
cp -r path/to/nuiitivet/skills/nuiitivet-app ~/.copilot/skills/nuiitivet-app
```

The skill is self-contained — `SKILL.md`, its topical references, and the linter
script travel together, so copying the whole directory is all that is needed.
Once installed, the assistant loads it whenever it writes or reviews Nuiitivet
code — no per-session setup.

## What it front-loads

`SKILL.md` opens with six core rules the assistant must not violate:

1. **One import root** — `import nuiitivet.material as nv`; reach every symbol
   through `nv`.
2. **UI components subclass `nv.ComposableWidget` and define `build(self)`** —
   no `StatelessWidget`/`StatefulWidget`, no `createState`/`initState`.
3. **State is `Observable`, and the UI binds to it — never push** — no
   `setState`, no `subscribe()` just to shove a value into a widget.
4. **Size, spacing, and alignment are widget *parameters*, not wrapper widgets**
   — no `Padding`/`SizedBox`/`EdgeInsets`. (`Container` *does* exist as a plain
   layout box; background/border/clipping are modifiers, not its job.)
5. **Decoration and behavior attach via `.modifier(...)` chained with `|`** — do
   not wrap a widget to decorate it.
6. **The app root is a factory, not an instance** — pass `App(content=build_root)`,
   never `App(content=build_root())`.

It links to topical references (layout, state, navigation, anti-patterns) the
assistant reads on demand. *Running* the app under hot reload and driving it while
you debug is the companion [`nuiitivet-debug`](nuiitivet_debug_skill.md) skill's
job, not this one.

## The idioms linter

The skill ships a linter that flags foreign-framework patterns and points at the
correct Nuiitivet idiom (warnings only — it does not edit code):

```bash
python skills/nuiitivet-app/scripts/check_idioms.py <files-or-dirs>
```

The skill instructs the assistant to run it as the final step of any edit and
resolve every finding by hand.

## See also

- [AI pair-programming](index.md) — where this skill fits the
  edit → see → act loop.
- [The `nuiitivet-debug` skill](nuiitivet_debug_skill.md) — the companion skill
  that runs, hot-reloads, and drives the app you write with this one.
- [Hot Reload](hot_reload.md) — the factory contract the skill's authoring
  guidance depends on.
