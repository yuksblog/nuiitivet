---
name: design-creator
description: Create or update a design document in docs/design/: the sections a design doc carries, the sentence test that decides where a fact lives, the order a promise rests on, standing alone, diagrams, the checklist.
---

# Design Creator

Creating and updating design documents in `docs/design/`. The pages are built
into the site and reached by link, not from the sidebar.

## What to Write

**The reader builds or changes the framework; they do not use it.** A design
doc carries these sections, in this order:

| Section | Carries |
| --- | --- |
| Purpose | What the subject is for. One paragraph directly under the subject's heading, with no heading of its own |
| Structure | The participants and their relations, who calls whom, what passes between them, drawn as a communication diagram in `mermaid`: boxes of one granularity, each edge labelled with the call or the thing passed; then a table with a row per box, Module then Role: the box's name at the subject's level (a group, a package, a file, a class, a function) and what it does |
| Sequence | The orders of steps the promises rest on, across threads or modules: one `####` per case, named as the case, each a `sequenceDiagram`. Present only where the subject has such an order |
| Promises | The rules the implementation must keep across modules, stated as present-state constraints, with no reason attached. What the user sees as a result is not one |

A page with several subjects nests the sections under each subject's heading.
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

A behaviour the reader would predict from the OS or the browser they already
use is written nowhere: not in the guide, which carries only what surprises,
and not in the design doc unless a module relation rests on it. Tab skipping
a hidden panel, a modal that traps Tab and hands focus back, are such
behaviours.

A design doc that grows past its name has started carrying a fact the test
sends elsewhere: what the user meets ("the selection stays until the next
click"), what an argument does, a measurement, a reason. Move it to its
place, not into a bigger doc.

**The order lives in a Sequence case, the invariant in the promise.** A
promise is checked against the Structure diagram and its own sentence. When
the check needs to know which step comes before which, that order is a case
under Sequence, and the promise keeps only what holds: "A superseded result
never lands", with the token check, the staging and the flush drawn above
it. An order that closes inside one module is the function's reader's and is
not drawn. A subject with more than three cases is two subjects.

**The outline comes first, and the headings are the outline.** Before any
prose, write the page's tree in the reply: the overview subject with its
modules, then each subject with its sections, the Sequence cases by name,
and under Structure the boxes of that subject's granularity. Each level divides its parent on one
axis, with no gap and no overlap, on the whole page; `##` and `###` are the
nodes and the prose only fills them. Written from the code instead, a page
ends up a docstring with reasons attached, and a structure hidden inside one
long section passes the heading check untouched.

**The first subject is the whole, the rest are its parts.** A page whose
subject fits one Structure has one `##`. A larger page opens with an
overview subject: a communication diagram whose boxes are the modules, a
table of each module's role, and the promises that bind them all. Each `##`
after it is one box of the overview, a module or a group of modules, drawn
one level finer: the modules of a group, or the classes of a module when
several of them talk to each other; never the functions of one class, whose
names go on the edges. A box is a unit that exchanges messages, and a
Sequence participant is a box of the subject's Structure or an actor; a
box's functions are the messages. A group box carries its name alone; its
modules are drawn in its own subject. An edge is labelled with the call, the
thing passed, or the relation (`is a`). Where
the parts share a mechanism (three modes on one glass), the
first subject is what they share, and its Structure is the overview. An
actor outside the code, the human or a thread, may stand beside the boxes.

**The subjects divide the participants.** A participant has one home
Structure, where its parts and its relations are drawn; another Structure
names it only as the endpoint of an edge, by its bare name. A draft whose
subjects are phases, with one participant drawn out in two Structures, is
divided by time, and is redrawn by module; the order the phases carried goes
into Sequence cases.

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

Layers, the relations between modules, and an order of steps across threads
or modules are drawn, as a `mermaid` fence. It renders on the site and on
GitHub, diffs as text, and a tool that never renders it can still read it.

- `flowchart` for Structure, as a communication diagram: boxes of one
  granularity, subgraphs for a layer or a group, the edge label naming the
  call or what is passed
- `sequenceDiagram` for a Sequence case, its participants the boxes of the
  subject's Structure, an `alt` for the branch the promise names
- a `text` fence for a small spatial nesting (boxes inside boxes) when the
  drawing *is* the point

`mkdocs build --strict` does not validate Mermaid syntax. Check a new diagram
in `mkdocs serve` or the GitHub preview.

## Checklist

- [ ] The outline was written in the reply before the edit; every heading in the diff is one of its nodes; `grep -n '^##' docs/design/<page>.md`, read top to bottom, shows each subject's Structure, its Sequence where it has one, and its Promises, and divides on one axis at each level
- [ ] Each promise is a rule the implementation must keep across more than one module; a surprise or a limit the user meets, or a fact of one function's caller or reader, is moved to its place; the guide and the docstrings open beside the draft
- [ ] Each subject's Structure has the diagram of relations and the table; the boxes of one diagram are one granularity, groups in the overview and modules or classes below it, never one class's functions; every Sequence participant is a box of the Structure; every box has a row, Module then Role, the Role a description and not a second name
- [ ] Each promise that rests on an order has that order as a `####` case under Sequence, or the order closes inside one module; the promise states what holds, not the steps
- [ ] No reason, no alternative, no history: `grep -nwE 'because|since|so that' docs/design/<page>.md`, every hit read, every reason deleted
- [ ] No link into `docs/guide/`, no issue number: `uv run pytest tests/test_design_docs_stand_alone.py`
- [ ] Structure drawn as `mermaid`; every new diagram rendered once
- [ ] One fact per sentence; no two joined by "and" or a colon
- [ ] `uv run --group docs mkdocs build --strict` passes
