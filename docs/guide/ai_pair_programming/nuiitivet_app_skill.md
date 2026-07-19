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

`SKILL.md` opens with five core rules the assistant must not violate:

1. **One import root** — `import nuiitivet.material as nv`; reach every symbol
   through `nv`.
2. **UI components subclass `nv.ComposableWidget` and define `build(self)`** —
   no `StatelessWidget`/`StatefulWidget`, no `createState`/`initState`.
3. **State is `Observable`, and the UI binds to it — never push** — no
   `setState`, no `subscribe()` just to shove a value into a widget.
4. **Size, spacing, and alignment are widget *parameters*, not wrapper widgets**
   — no `Padding`/`SizedBox`/`Container`/`EdgeInsets`.
5. **Decoration and behavior attach via `.modifier(...)` chained with `|`** — do
   not wrap a widget to decorate it.

It also covers hot-reload authoring (write a root **factory**, not an instance)
and links to topical references (layout, state, navigation, anti-patterns) the
assistant reads on demand.

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
- [Hot Reload](hot_reload.md) — the factory contract the skill's authoring
  guidance depends on.
