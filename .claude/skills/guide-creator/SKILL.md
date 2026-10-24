---
name: guide-creator
description: Create or update a guide page in docs/guide/: what a guide carries, sample and screenshot requirements, linking between pages, the checklist.
---

# Guide Creator

Creating and updating guides in `docs/guide/`.

## What to Write

**The reader uses the framework; they do not build it.** A guide answers *how
do I do this* and *what will surprise me*. Design rationale belongs in
`docs/design/`: why the API is shaped so, what the internal cells are.

**One sentence test decides where a fact lives.** It is a rule the
framework's implementation must keep, across more than one module: the
design doc's promises. It is a surprise or a limit a user of the app meets:
the guide. It is what a caller of one function can observe: the docstring.
It is what a reader of one function can see: the code. The reason a rule was
chosen over an alternative lives in the issue that decided it, in none of the
four. One fact can yield two sentences, the rule for the design doc and the
surprise for the guide: "alignment is written on the container" and "the
alignment written is the container's, not the widget's".

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

**A surprise is written where the reader meets it, in the shape of what
they see.** Its place follows from when they meet it:

| The reader meets it | Where | Form |
| --- | --- | --- |
| on the first round, whoever they are | the step | one sentence after the action, as what they see ("the selection stays until the next click"); no callout |
| only with a particular widget or setup | the way's section in the reference, or a case below it | a heading when it runs a few lines, a sentence in the way otherwise |
| as a refusal, or as nothing happening | the page's last lists ("What it refuses", "What does nothing") | one line each; the reader searches backwards from the symptom |
| as a loss they cannot see coming: no confirmation, an edit that silently stops applying | a callout in the step | one or two on a page, naming the loss |
| as a question, "why did nothing happen?" | an "If …" heading in the reference | the symptom in the heading |

A callout stops the reader; it earns that only where missing it costs
something with no symptom to search for. A refusal the badge explains is a
list line. A page with three callouts has put list lines and "If …" sections
into boxes. A sentence that opens with "Note that" has left the instruction:
write the symptom and the next action in the voice of the step, and never
the rule behind it.

**The spine comes first, and the headings are the spine.** Before any prose,
write the page's outline in the reply and mark each level with one of two
shapes. A *sequence*, when the reader does every sibling in order: the
headings are the steps, each one's result is the next one's start, and no
step is missing (mark the function, pass arguments, report progress, cancel,
handle an error). A *set*, when the reader does one sibling: the headings are
the choices on one axis, and no two overlap (`@nv.worker` or `@nv.server`;
the rows of a chooser table). One page holds both, at different levels, and
the surprise goes where the reader would hit it. Written from the code
instead, a page names every argument in the order of the signature and
answers none of the reader's questions first.

**Each level is one shape, chosen by the reader's question there.** "Then
what?" makes the level a sequence, its headings the steps. "Which one?" makes
it a set, its headings the choices, led by a line or a table that picks among
them; a set whose choices are a few lines each is tabs, not headings. A
heading of a sequence names one action, and its section carries that action
and nothing else: not the step before it, not a key the reader presses only
in another case.

**A step's ways sit under it while they stay small.** A step with several
ways holds them one level below as a set while each is a few lines and the
step still reads as one action. Once the ways outgrow the step, the reader
has to read every way before they have done the step once. Then the step
shows the one way a first reader takes and names the section that holds the
others, and every way becomes a section of a reference of ways after the
round, a set with its cases one level below (`### Reorder`, then `#### Over a
Stack`). The reference of ways comes before the vocabulary tables, every
gesture, everything it writes. A reference that holds several lists is a
set, one heading per list.

**A sequence's headings are numbered; a set's are not.** `## 1. Enter the
mode`, `## 2. Mark the place`: the number says the reader does every sibling
in order, and its absence says they pick one. A level with a single step
takes no number.

**Each heading names what the reader wants to do there.** A reader scans the
table of contents for their problem; a clever heading hides it.

| Instead of | Write |
| --- | --- |
| The rule | *(no heading — open with the code)* |
| Two spellings, two meanings | Choosing how invalid text behaves |
| Wrapping operators compose into the chain | Waiting for the typing to settle |
| Two things that are not this | Restricting and reshaping the text itself |
| The one trap | If the field will not accept typing |
| *(a gesture table as the first section)* | the round first; "Every gesture" last |
| Mark the place *(enter, click, walk, or drag)* | Enter the mode / Mark the place, with Aim at a covered widget a level below |

**The opening says what the thing is.** One or two sentences, then the code
or the first step. Where that sentence does not carry the intent, say when
the reader is stuck and how this gets them out: "Telling an agent *where* is
the hard part of telling it what to do; comment mode puts the instruction on
the app itself." A summary of the page, a list of its features, or a remark a
section will make again is not an opening: the reader came for the thing,
and the headings carry the rest.

**Open with working code, not a principle.** The shortest complete example
first; comments carry the point (`# bind this` / `# use this`). Prose after,
only for what the code cannot show.

**A reference closes the page.** A table or list that enumerates a
vocabulary, every gesture, every command, every option, is a dictionary: the
reader can use it only once they know what the feature is and how one round
of it goes. It sits after the round and any reference of ways, as the page's
last section, under a heading such as "Every gesture". The one table that
opens a page is a chooser, the "You want to… / Read" table of a hub, since
there the reader's first act is to choose. A page written table-first hands
the reader the keys before the actions they belong to.

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

**Open with the thing and its verb, not an abstraction of it.** "The line
break is a key gesture" makes the reader translate back to "Shift+Enter breaks
the line"; write the second.

**A sentence carries one fact, whole.** Two facts joined by "and" or a colon
are two facts in a sentence that got shorter and harder. Give each its own
sentence, or delete the one the reader does not need.

**Within a section, what it does before how and the concrete before the
abstract**, each only when the reader lacks it.

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
The reading order is the order of use: setup once, then the pages in the
order a round meets them, with a reference page, the CLI, every command,
last. The section index is the one page that opens with a table, the
chooser.

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

## Review by a Fresh Reader

The author's own reread misses what the author folded in: a step holding
three actions, an opening that summarises the page, a key the reader presses
only in another case. Before the draft reaches the user, hand it to a
subagent that has no other context: this skill file and the page, nothing
else, with the instruction to hold every item of the checklist below against
the page and report each miss by heading and sentence. Fix what it finds,
then present. A page the agent passes is not finished; a page it has not
read is not reviewed.

## Checklist

- [ ] No design rationale, no doctrine headings — the reader is a user; the surprise or the limit a user meets is here even when a design rule produced it
- [ ] Each surprise sits where the reader meets it, as what they see: in the step, in the way, in the last lists, or under an "If …" heading; at most two callouts on the page, each naming a loss with no symptom
- [ ] The outline was written in the reply before the edit, each level marked sequence or set; every heading in the diff is one of its nodes and names a task; `grep -n '^#' docs/guide/<page>.md`, read top to bottom: a sequence with no missing step, a set with no overlapping choice, on the whole page
- [ ] Each step one action; its ways sit one level below while each is a few lines; ways that outgrew the step moved to a reference of ways after the round, its cases one level below, and the step shows one and names that section
- [ ] Sequence headings are numbered, set headings are not
- [ ] Opens with what the thing is, in a sentence or two, then the code or the first step; no summary of the page
- [ ] Every table or list that enumerates a vocabulary sits after the round and any reference of ways, as the page's last section; the only table that opens a page is a chooser on a hub
- [ ] Every snippet executed, including inline ones
- [ ] Short sentences, one fact each, dense throughout; a fact repeated only where two places are far apart
- [ ] Each sentence checked against `docs/design/` and the docstrings, both open beside the draft; what either already says is deleted
- [ ] Each paragraph opens with the thing and its verb; one fact per sentence, no two joined by "and" or a colon
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
- [ ] A fresh-context subagent, given only this skill and the page, held the checklist against it, and its findings are fixed
