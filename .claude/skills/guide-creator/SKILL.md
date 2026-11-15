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

### What belongs on the page

**One sentence test decides where a fact lives.** It is a rule the
framework's implementation must keep, across more than one module: the
design doc's promises. It is a surprise or a limit a user of the app meets:
the guide. It is what a caller of one function can observe: the docstring.
It is what a reader of one function can see: the code. The reason a rule was
chosen over an alternative lives in the issue that decided it, in none of the
four. One fact can yield two sentences, the rule for the design doc and the
surprise for the guide: "alignment is written on the container" and "the
alignment written is the container's, not the widget's".

A behaviour the reader would predict from the OS or the browser they already
use is written nowhere: not in the guide, which carries only what surprises,
and not in the design doc unless a module relation rests on it. Tab skipping
a hidden panel, a modal that traps Tab and hands focus back, are such
behaviours.

Cut on sight:

- a behaviour the OS or the browser already has ("Tab skips a closed panel")
- a behaviour the Material Design 3 spec defines (a shape morph, a colour
  transition, a state layer), unless the reader must do something to get it
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

### The example

**The example needs the tool.** A Save button whose handler could show the
snackbar on its next line needs neither a `State` nor a `Topic`, and the
reader asks why the page exists. Pick the scene where the reader is stuck
without the tool: a worker thread finishes a file, and no handler of the
screen is running.

**The scene is one every reader has met.** A snackbar after a save, a search
box, a progress bar. The reader then spends their attention on the tool, not
on the scene.

**The page rests on nothing its section treats as optional.** A page that
explains events through a ViewModel loses the reader who never adopted one.

**Real code over illustrative code.** `filter(str.isdigit, initial="1")`
teaches more than `filter(_is_int, initial="0")` with an invented helper.

### The structure

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
in another case. An action is one thing the reader sets out to do, not one
line of code: declaring a `Topic` and calling `publish()` are one step,
"Publish when a file is done".

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
| Two spellings, two meanings | Choosing how invalid text behaves |
| Wrapping operators compose into the chain | Waiting for the typing to settle |
| Two things that are not this | Restricting and reshaping the text itself |
| The one trap | If the field will not accept typing |
| *(a gesture table as the first section)* | the round first; "Every gesture" last |
| Mark the place *(enter, click, walk, or drag)* | Enter the mode / Mark the place, with Aim at a covered widget a level below |

**A surprise is written where the reader meets it, in the shape of what
they see.** Its place follows from when they meet it:

| The reader meets it | Where | Form |
| --- | --- | --- |
| on the first round, whoever they are | the step | one sentence after the action, as what they see ("the selection stays until the next click"); no callout |
| after the round, whoever they are: the app grows a second screen, or they write the call another way | a "Keep in mind" section after the round | the fact, the rule or the request as the heading ("A publish reaches the screens subscribed at that moment", "Subscribe a method, not a lambda"); the fact under it, with a scene where one helps; no workaround for a behaviour that is correct |
| only with a particular widget or setup | the way's section in the reference, or a case below it | a heading when it runs a few lines, a sentence in the way otherwise |
| as a refusal, or as nothing happening | the page's last lists ("What it refuses", "What does nothing") | one line each; the reader searches backwards from the symptom |
| as a loss they cannot see coming: no confirmation, an edit that silently stops applying | a callout in the step | one or two on a page, naming the loss |
| only in some setups, as a question, "why did nothing happen?" | an "If …" heading in the reference | the symptom in the heading; what they see without the fix, then the fix |

**"Keep in mind" or "If …": who meets it decides.** What every reader meets
sooner or later goes under "Keep in mind", stated as the fact or the rule;
the reader who knows it never sees the symptom. A symptom only some setups
produce goes under an "If …" heading: the reader who has it searches
backwards from it, and the others skip it.

**A page beside a known tool closes with when the known tool is right.** A
short list after "Keep in mind", under a heading such as "When a State is
the right tool".

A callout stops the reader; it earns that only where missing it costs
something with no symptom to search for. A refusal the badge explains is a
list line. A page with three callouts has put list lines and "If …" sections
into boxes. A sentence that opens with "Note that" has left the instruction:
write the symptom and the next action in the voice of the step, and never
the rule behind it.

**A feature the framework runs on its own has two parts, in this order: what
the reader gets with no code, then what they change.** The first part is a
table of what each widget yields ("a checkbox: its role and its state, no
words"), and it is where the reader learns whether their app needs the second
part at all. A page that carries only the second part tells the reader to fix
something they cannot see is broken. A section of the second part opens with
what the reader sees or hears without the fix, then gives the fix.

**A dictionary closes the page; a model opens its part.** A table or list
that enumerates a vocabulary, every gesture, every command, every option, is
a dictionary: the reader can use it only once they know what the feature is
and how one round of it goes. It sits after the round and any reference of
ways, as the page's last section, under a heading such as "Every gesture". A
table that carries the reader's model of the feature is not a dictionary: the
"You want to… / Read" chooser of a hub, the OS × place matrix of where a
badge shows, the widget × what-is-read table of a screen-reader page. It
opens the part it belongs to, where the reader forms the picture the rest
rests on. A page that puts a gesture table first hands the reader the keys
before the actions they belong to.

**Facts that are a cross product go in one table.** When the result depends
on several things the reader must cross (the OS, the place, the way), the
opening names the ways and says the result varies, each section carries only
how to do its way, and one table holds every combination, in a section of
its own after the ways ("Where each icon shows").
Written as prose, every sentence needs a condition, and the same fact
surfaces in the opening, in each section and in the last list. The headings
name the ways in the words the opening used. A sentence that restates a
table cell is deleted.

### The opening

**The opening says what the thing is.** One or two sentences, then the first
step. Where that sentence does not carry the intent, say when the reader is
stuck and how this gets them out: "Telling an agent *where* is the hard part
of telling it what to do; comment mode puts the instruction on the app
itself." A summary of the page, a list of its features, or a remark a section
will make again is not an opening: the reader came for the thing, and the
headings carry the rest.

**The exception is a page for a tool that stands beside one the reader
knows: it opens with the hole.** In short paragraphs: what the known tool
does for them, what it does not cover, the scene where they are stuck, then
the new tool and who writes which line. The first paragraphs restate what
the reader knows; the hole is seen against them. The opening of
`docs/guide/state-management/topic.md` is the model: a `State` is what the
screen shows; a snackbar is shown by a call from an event handler; a worker
imports files, the reader wants a snackbar for each, and a `State` does not
fit; the import publishes to a `Topic`; a subscribed method shows the
snackbar. One sentence says why the known tool does not fit. What goes wrong
when it is forced into the scene (a value shown once, values skipped) stays
out of the opening: it follows from the hole and buries it.

**The opening is prose.** No code block comes before the first heading. The
reader does not yet know why they would read it.

### Code and diagrams

**The page lists the whole sample nowhere.** Each step shows the lines that
step adds. The page names the sample's path once, and the reader opens the
file for the rest. A full listing at the top is skipped, and one at the end
repeats the file.

**A sentence or two comes before every code block.** They say what the
reader does in the step and what the block shows. What surprises goes after
the block. A block directly under a heading leaves the reader to work out
what to look for.

**A snippet is code the reader would write in their own app.** A widget
invented to exhibit an API is not, and its section goes. Code written the
wrong way is not shown either, not even as the "before" of a comparison:
half the page becomes code nobody should write. Work outside the page's
subject may be a marked stand-in (`time.sleep(0.5)  # stand-in for importing
one file`).

**A comment marks what the page teaches** (`# on the worker thread`). A line
that changed only because the framework changed stays bare: what the change
was about is invisible to the reader.

**Every snippet runs.** Execute each one before shipping, the inline ones too.
A snippet that drifted from the API is worse than none.

**Who calls what, and when, is a sequence diagram.** Where the framework
calls the reader's method later, or on another thread, the code alone does
not show it. Draw a `mermaid` `sequenceDiagram` where the round starts,
before its first step. It starts from the user's action ("You: press
Import") and ends at what they see, and it notes the thread where the thread
changes. `mkdocs build --strict` does not validate Mermaid syntax.
Check a new diagram in `mkdocs serve` or the GitHub preview. A node id that
is a Mermaid keyword does not parse: `style`, `call`, `interpolate`, `end`,
`class`, `click`, `default`, `subgraph`, `direction`. A `;` inside a label
breaks a `sequenceDiagram`.

### Sentences

**Each sentence starts from the app author.** What they want ("you want a
snackbar each time a file is done"), what they write ("the import publishes
when a file is done"), what they see in the running app ("a snackbar appears
for each file"). A sentence about how a framework type works inside ("the
`Topic` holds no value", "within one frame") is rewritten as what the author
observes. Saying what a tool is for is the author's view: "A `State` is what
the screen shows."

**A sentence names the line the reader writes.** "The import publishes the
file name. The screen subscribes a method." names `publish` and `subscribe`.
"Your logic says what happened, and the screen does its part" names neither,
and the reader cannot tell which call it means. Everyday words; no word pair
coined for the page.

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

**A sentence carries one fact, whole.** Two facts that would each stand
alone, joined by "and" or a colon, are two facts in a sentence that got
shorter and harder. Give each its own sentence, or delete the one the reader
does not need. An action joined to its result is one fact ("Press Import,
and a snackbar appears for each file"). So is a statement with its examples
after a colon.

**Within a section, what it does before how and the concrete before the
abstract**, each only when the reader lacks it.

**Wrap by the rendered width.** A link counts as its text; the URL adds
nothing. Counting the URL breaks a short sentence in two around its link.

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

A conceptual guide carries no screenshot; do not add it to
`scripts/docs/render_layout_images.py`. A `mermaid` diagram is not a
screenshot.

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
- **Root factory** (hot reload): `Window(content=...)` takes a factory the dev
  runner can run again after a reload, never a widget instance. A new sample
  builds the UI in a module-level `def build_root() -> nv.Widget:` and passes
  it uncalled:

  ```python
  def build_root() -> nv.Widget:
      return nv.Text("Hello")


  app = nv.App(nv.Window(content=build_root))
  ```

  - The dev runner re-fetches a module-level function or a widget class *by
    name* from the reloaded module, so an edit anywhere in it applies.
  - A `lambda` or a function inside `main()` cannot be re-fetched, and the
    old one runs again. An edit to a widget it builds applies; an edit to its
    own line does not. Use one only where the root needs a value made in
    `main()` (`content=lambda: Screen(state)`).
  - `content=build_root()` (with the call) passes an instance, and no edit
    reaches the window; `tests/test_samples_root_factory.py` catches it.
  - **Verify every new or changed sample end-to-end**: launch it under
    `python -m nuiitivet.dev run`, edit the UI, confirm the edit lands in
    `reload_log` or `describe_tree`. Only the live check catches a root the
    reloader cannot rebuild.
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
subagent that has no other context.

Name the files it may read: this skill file, the page, and the docs pages a
reader has passed before it. Say that every other path is off limits. With
`src/` or `samples/` open, it fills each gap from the code and stops finding
what a user stumbles on.

Tell it to hold every item of the checklist below against the page, to sort
every sentence into the author's view or the framework's view, and to report
each miss by heading and sentence. It skips the items that need a tool or a
path it may not read; those stay with the author.

Fix what it finds inside the edit the user agreed to. A finding that changes
the page's shape (a heading renamed, sections reordered or split) is reported
as a proposal, with the sentence that would change. A finding on a passage
the user wrote changes the flagged words only: every point the user made is
still there as a sentence afterwards.

A page the agent passes is not finished; a page it has not read is not
reviewed.

## Checklist

- [ ] No design rationale, no doctrine headings — the reader is a user; the surprise or the limit a user meets is here even when a design rule produced it
- [ ] Each surprise differs from what the OS or the browser does; a behaviour that matches them is deleted
- [ ] The example needs the tool, in a scene every reader has met; nothing the section treats as optional is assumed
- [ ] Each surprise sits where the reader meets it, as what they see: in the step, under "Keep in mind", in the way, in the last lists, or under an "If …" heading; a "Keep in mind" heading is the fact, the rule or the request, with no workaround for a correct behaviour; at most two callouts on the page, each naming a loss with no symptom
- [ ] The outline was written in the reply before the edit, each level marked sequence or set; every heading in the diff is one of its nodes and names a task; `grep -n '^#' docs/guide/<page>.md`, read top to bottom: a sequence with no missing step, a set with no overlapping choice, on the whole page
- [ ] Each step one action, one thing the reader sets out to do; its ways sit one level below while each is a few lines; ways that outgrew the step moved to a reference of ways after the round, its cases one level below, and the step shows one and names that section
- [ ] Sequence headings are numbered, set headings are not
- [ ] Opens with what the thing is, or with the hole in the tool the reader knows, its symptoms left out; prose only above the first heading; no summary of the page
- [ ] Every table or list that enumerates a vocabulary sits after the round and any reference of ways, as the page's last section; a table that carries the reader's model (a chooser, a matrix, what each widget yields) opens the part it belongs to
- [ ] A feature the framework runs on its own: what the reader gets with no code comes first, as a table of what each widget yields; every section that changes a default opens with what is seen or heard without the fix, then the fix
- [ ] No full listing of the sample, its path named once; a sentence or two before every code block; no snippet written the wrong way or invented to exhibit an API; comments only on what the page teaches
- [ ] Every snippet executed, including inline ones
- [ ] Every `mermaid` diagram rendered; the round's diagram starts from the user's action and notes the thread
- [ ] Each sentence starts from what the app author wants, writes or sees, and names the line they write; none says how a framework type works inside
- [ ] Short sentences, one fact each, dense throughout; a fact repeated only where two places are far apart
- [ ] Each sentence checked against `docs/design/` and the docstrings, both open beside the draft; what either already says is deleted
- [ ] Each paragraph opens with the thing and its verb; one fact per sentence, no two that stand alone joined by "and" or a colon
- [ ] Sample exists and runs; guide code blocks match it
- [ ] Root is a factory passed uncalled, never an instance; a new sample uses a module-level `build_root`
- [ ] Every new or changed sample verified end-to-end under `python -m nuiitivet.dev run`: an edit to the UI hot-reloads into the live tree
- [ ] Only `import nuiitivet.material as nv` — no `import nuiitivet`, no deep import
- [ ] Correct kind applied (conceptual guides: no screenshots)
- [ ] Visual guides: `render_layout_images.py` updated, screenshots generated and embedded
- [ ] Page in the `mkdocs.yml` nav and in the section `index.md` reading order
- [ ] Next Steps carries only the next page plus the overview; no back-link, no see-also callout
- [ ] One entrance to a concept page; many only to a lookup page
- [ ] `uv run mkdocs build --strict` passes
- [ ] A fresh-context subagent, given only this skill, the page and the docs pages before it, held the checklist against it; its findings inside the agreed edit are fixed, the others reported
