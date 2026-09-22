---
name: guide-creator
description: Create or update a guide page in docs/guide/: what a guide carries, sample and screenshot requirements, linking between pages, the checklist.
---

# Guide Creator

Creating and updating guides in `docs/guide/`.

## What to Write

**The reader uses the framework; they do not build it.** A guide answers *how
do I do this* and *what will surprise me*. Design rationale belongs in
`docs/design/`: why the API is shaped so, what the alternative would have
cost, what the internal cells are.

Cut on sight:

- internal mechanics ("two cells would need an echo guard so they do not chase each other")
- principles stated as doctrine rather than instruction ("a widget's value type follows its primary input mechanism")
- justifications for why a parameter exists at all
- instructions to the coding agent; the skills (`skills/`) carry those, a guide
  addresses the human

**Keep the symptom where a rationale would have gone; a sentence the reader
can picture beats an exact one.** "The field ends up reformatting itself under
the user's cursor" is something the reader will hit; "two observables
describing one thing" is not. Reach for the exact form only where the picture
would be wrong.

**Headings name what the reader wants to do.** A reader scans the table of
contents for their problem; a clever heading hides it.

| Instead of | Write |
| --- | --- |
| The rule | *(no heading — open with the code)* |
| Two spellings, two meanings | Choosing how invalid text behaves |
| Wrapping operators compose into the chain | Waiting for the typing to settle |
| Two things that are not this | Restricting and reshaping the text itself |
| The one trap | If the field will not accept typing |

**Sibling headings divide their parent on one axis**, with no gap and no
overlap. Check the whole page, not only the section touched.

**Open with working code, not a principle.** The shortest complete example
first; comments carry the point (`# bind this` / `# use this`). Prose after,
only for what the code cannot show.

**Every snippet runs.** Execute each one before shipping, the inline ones too.
A snippet that drifted from the API is worse than none.

**Real code over illustrative code.** `filter(str.isdigit, initial="1")`
teaches more than `filter(_is_int, initial="0")` with an invented helper.

**Short sentences, dense from the first line to the last.** Each sentence
carries one fact the reader does not have. A fact is stated once; it is
repeated only where the two places are far apart.

| Instead of | Write |
| --- | --- |
| It is important to note that the value must be an `int` | The value must be an `int` |
| You may want to consider using `filter()` here | Use `filter()` |
| There are cases in which the field will not accept typing | The field sometimes refuses typing |
| This is done in order to avoid the value being reformatted | *(cut — or name the symptom the reader sees)* |

## Widget Showcase Pages

`docs/guide/design-system/material_widgets.md` is a showcase, not a reference.
Per widget: one sentence of what it is, the one thing a reader must know not
to misuse it, a screenshot, the API Reference link. About 15 lines;
`StandardSideSheet` is the upper bound.

Everything else goes in the class docstring. Verify it reaches the rendered
reference:

```bash
uv run mkdocs build --strict -d /tmp/site
grep -c 'id="nuiitivet.material.<Name>"' /tmp/site/api/material/index.html
```

A module-level constant does not render (mkdocstrings and the lazy
`__getattr__` package); never point a guide at one.

Do not name a widget the project does not publish, even for contrast.

## Guide Kinds

| Kind | Directories | Samples | Screenshots |
| --- | --- | --- | --- |
| **Visual** | `layout/`, `modifiers/`, `design-system/`, `navigation/`, `overlay/`, `window/`, `advanced/` | `samples/<topic>/` | Yes, via the harness |
| **Conceptual** | `state-management/`, `concurrency.md` | `samples/state-management/<page>.py`, one per page, same basename | No |

A conceptual guide carries no image; do not add it to
`scripts/docs/render_layout_images.py`.

A hub page only routes (`docs/guide/concurrency.md`); it carries no sample and
no code. The chooser table is the content. An example belongs on the page the
hub routes to; a copy on the hub is a second copy to keep in step.

## Sample Code

Every code example is backed by an executable file.

- A complete, runnable application.
- Visual guides: supports the screenshot harness (`main(png_path: str = "")`).
- **Imports**: the single design-system root, once, every symbol as `nv.<Name>`:

  ```python
  import nuiitivet.material as nv

  nv.Column([nv.Text("Hello"), nv.Button("Click")])
  ```

  - No separate `import nuiitivet`, no deep import
    (`from nuiitivet.material.buttons import Button`). Every public symbol,
    modifiers included (`nv.background`, `nv.corner_radius`), is reachable
    from `nv`; `tests/test_public_imports.py` enforces it.
  - Guide code blocks match the sample (the Imports section of
    `docs/guide/index.md`).
  - A symbol not reachable as `nv.<Name>` is a bug in
    `src/nuiitivet/material/__init__.py`, not a reason to deep-import.
- **Root factory** (hot reload): the UI is built in a module-level
  `def build_root() -> nv.Widget:` and passed uncalled, `nv.Window(content=build_root)`:

  ```python
  def build_root() -> nv.Widget:
      return nv.Text("Hello")


  app = nv.App(nv.Window(content=build_root))
  ```

  - The dev runner re-fetches the factory *by name* from the reloaded module.
    A `lambda` or a function inside `main()` cannot be re-fetched: the app
    launches, and edits to the UI silently stop applying.
  - `content=build_root()` (with the call) passes an instance and breaks
    reload the same way; `tests/test_samples_root_factory.py` catches that
    half statically.
  - **Verify every new or changed sample end-to-end**: launch it under
    `python -m nuiitivet.dev run`, edit `build_root`, confirm the edit lands
    in `reload_log` or `describe_tree`. Only the live check catches a factory
    the reloader cannot re-fetch.
  - Guide code blocks use the same `build_root` form.

## Screenshots (visual guides only)

1. Add the sample to `SAMPLES` in `scripts/docs/render_layout_images.py`:

   ```python
   ("samples/<topic>/basic_usage.py", "<topic>_basic.png")
   ```

2. Run `uv run scripts/docs/render_layout_images.py`
3. Verify the image lands in `docs/assets/`
4. Embed it: `![Basic Usage](../../assets/<topic>_basic.png)`

## Linking Between Pages

Cross-links rot. With N sibling pages on interchangeable tools, honest "see
also" lists are an N×N job. The rules that keep it linear:

**"Next Steps" is the reading order, not a see-also list.** It carries the next
page in the section's `index.md` order, plus the section overview, nothing
else. A page the reader has passed, or one four steps ahead, is not there.

**A body link earns its sentence.** Link sideways where the page stops short
and names what continues ("that second case ... is Background Work"), or where
it leans on a specific section elsewhere (link the anchor, not the page). No
reciprocal link because the other page points here; a "Related" or "See also"
callout added for symmetry is what this rule prevents.

**When both sides need routing, route through a hub.** A page that answers
"which of these do I use?" (`docs/guide/concurrency.md`) is linked from the
section index, and each tool page links up to it at most once: N edges instead
of N².

**A concept has one entrance; a lookup has many.** A page that explains one
thing is reached from one place. A page the reader searches backwards from, an
index or a chooser table, is reached from every page it answers for; that is
the design.

## New Pages

Add the page to the `nav` in `mkdocs.yml` and to the section `index.md`
reading order. Then fix the **Next Steps** of the page it now follows.

## Checklist

- [ ] No design rationale, no doctrine headings — the reader is a user
- [ ] Headings name a task, not a principle
- [ ] Sibling headings divide their parent on one axis, no gap, no overlap — checked on the whole page, not only the section touched
- [ ] Opens with working code
- [ ] Every snippet executed, including inline ones
- [ ] Short sentences, one fact each, dense throughout; a fact repeated only where two places are far apart
- [ ] Sample exists and runs; guide code blocks match it
- [ ] Root is a module-level `build_root` passed uncalled — no lambda, no local factory
- [ ] Every new or changed sample verified end-to-end under `python -m nuiitivet.dev run`: a `build_root` edit hot-reloads into the live tree
- [ ] Only `import nuiitivet.material as nv` — no `import nuiitivet`, no deep import
- [ ] Correct kind applied (conceptual guides: no screenshots)
- [ ] Visual guides: `render_layout_images.py` updated, screenshots generated and embedded
- [ ] Page in the `mkdocs.yml` nav and in the section `index.md` reading order
- [ ] Next Steps carries only the next page plus the overview; no back-link, no see-also callout
- [ ] One entrance to a concept page; many only to a lookup page
- [ ] `uv run mkdocs build --strict` passes
