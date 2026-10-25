---
name: design-creator
description: Create or update a design document in docs/design/: the three sections a design doc carries, the sentence test that decides where a fact lives, standing alone, diagrams, the checklist.
---

# Design Creator

Creating and updating design documents in `docs/design/`. The pages are built
into the site and reached by link, not from the sidebar.

## What to Write

**The reader builds or changes the framework; they do not use it.** A design
doc carries three sections, in this order:

| Section | Carries |
| --- | --- |
| Purpose | What the subject is for. One paragraph directly under the subject's heading, with no heading of its own |
| Structure | The relations between the modules or participants, who calls whom, what passes between them, drawn as `mermaid`; then a table of each one's role |
| Promises | The rules the implementation must keep across modules, stated as present-state constraints, with no reason attached. What the user sees as a result is not one |

A page with several subjects nests the three under each subject's heading.
What the subjects share is a subject of its own, under its own heading
before them, so the page's top level stays on one axis.

**One sentence test decides where a fact lives.** It is a rule the
framework's implementation must keep, across more than one module: the
design doc's promises. It is a surprise or a limit a user of the app meets:
the guide. It is what a caller of one function can observe: the docstring.
It is what a reader of one function can see: the code. The reason a rule was
chosen over an alternative lives in the issue that decided it, in none of the
four. One fact can yield two sentences, the rule for the design doc and the
surprise for the guide: "alignment is written on the container" and "the
alignment written is the container's, not the widget's".

A design doc that grows past its name has started carrying a fact the test
sends elsewhere: what the user meets ("the selection stays until the next
click"), what an argument does, a measurement, a reason. Move it to its
place, not into a bigger doc.

**The outline comes first, and the headings are the outline.** Before any
prose, write the page's tree in the reply: each subject with its three
sections, and under Structure the participants on the axis the subject has,
its layers, its phases or its modules. Each level divides its parent on one
axis, with no gap and no overlap, on the whole page; `##` and `###` are the
nodes and the prose only fills them. Written from the code instead, a page
ends up a docstring with reasons attached, and a structure hidden inside one
long section passes the heading check untouched.

**A promise is a constraint, not a decision.** "The tree is never mutated."
is complete. "The tree is never mutated, since a mutated tree would drift
from the code" carries the reason into the doc; the reader who wants it has
the issue.

**Short sentences, dense from the first line to the last.** Each sentence
carries one fact the reader does not have. A fact is stated once; it is
repeated only where the two places are far apart.

**Open with the thing and its verb, not an abstraction of it.** "Site
capture is a construction-time concern" makes the reader translate back to
"the runner wraps `Widget.__init__` and records the frames"; write the second.

**A sentence carries one fact, whole.** Two facts joined by "and" or a colon
are two facts in a sentence that got shorter and harder. Give each its own
sentence, or delete the one the reader does not need.

## Standing Alone

A design doc does not point at the guide and does not cite an issue number:
write what the pointer would have said. Links between design docs are fine.
Enforced by `tests/test_design_docs_stand_alone.py`.

## Diagrams

Layers, the relations between modules, and a sequence across threads are
drawn, as a `mermaid` fence. It renders on the site and on GitHub, diffs as text, and
a tool that never renders it can still read it.

- `flowchart` with subgraphs for structure
- `sequenceDiagram` for protocols
- a `text` fence for a small spatial nesting (boxes inside boxes) when the
  drawing *is* the point

`mkdocs build --strict` does not validate Mermaid syntax. Check a new diagram
in `mkdocs serve` or the GitHub preview.

## Checklist

- [ ] The outline was written in the reply before the edit; every heading in the diff is one of its nodes; `grep -n '^##' docs/design/<page>.md`, read top to bottom, shows each subject's Structure and Promises, and divides on one axis at each level
- [ ] Each promise is a rule the implementation must keep across more than one module; a surprise or a limit the user meets, or a fact of one function's caller or reader, is moved to its place; the guide and the docstrings open beside the draft
- [ ] Each subject's Structure has the diagram of relations and the table of roles
- [ ] No reason, no alternative, no history: `grep -nwE 'because|since|so that' docs/design/<page>.md`, every hit read, every reason deleted
- [ ] No link into `docs/guide/`, no issue number: `uv run pytest tests/test_design_docs_stand_alone.py`
- [ ] Structure drawn as `mermaid`; every new diagram rendered once
- [ ] One fact per sentence; no two joined by "and" or a colon
- [ ] `uv run --group docs mkdocs build --strict` passes
