---
name: design-creator
description: Create or update a design document in docs/design/: what a design doc carries and leaves out, standing alone, diagrams, the checklist.
---

# Design Creator

Creating and updating design documents in `docs/design/`. The pages are built
into the site and reached by link, not from the sidebar.

## What to Write

**The reader builds or changes the framework; they do not use it.** A design
doc carries the core ideas: what the design is and how it is realised. API
and procedure appear only as far as the design needs them.

Cut on sight, and move it down to the place whose job it is:

- what an argument does, however it is phrased — the docstring. The design
  doc says why the widget is built as it is: a text field keeps its own
  caret because a bound `str` cannot carry one, and the three write-back
  behaviours the docstring lists all follow from that one reason
- step-by-step mechanics and measurements — the guide, or the code
- the story of how a rule was found — nowhere; state the rule as present-state design

A design doc that grows past its name has started carrying procedure or API
reference. Move the surplus down, not into a bigger doc.

**The outline comes first, and the headings are the outline.** Before any
prose, write the section's tree in the reply: at the root, what the thing is
and the rule it follows; below it, the mechanism divided on the axis the
subject has, its layers, its phases, or its participants. Each level divides
its parent on one axis, with no gap and no overlap, on the whole page; `##`
and `###` are the nodes and the prose only fills them. Written from the code
or from a fixed what/how template instead, a page ends up a docstring with
reasons attached, and a structure hidden inside one long section passes the
heading check untouched.

**A sentence the reader can picture beats an exact one.** "The field ends up
reformatting itself under the user's cursor" lands; "two observables describing
one thing" does not. Reach for the exact form only where the picture would be
wrong.

**Short sentences, dense from the first line to the last.** Each sentence
carries one fact the reader does not have. A fact is stated once; it is
repeated only where the two places are far apart.

**Open with the thing and its verb, not an abstraction of it.** "The line
break is a key gesture" makes the reader translate back to "Shift+Enter breaks
the line"; write the second.

**Cutting means deleting, not compressing.** Two facts joined by "and" or a
colon are still two facts, in a sentence that got shorter and harder. Delete
the sentence the reader does not need and leave the other whole.

**A reason is written only where a choice was made.** "Shift+Enter breaks the
line." is complete; a reason on a fact that had no alternative dresses the
outcome up as a decision.

**Within a node, the fact before its reason and the concrete before the
abstract**, each only when the reader lacks it.

## Standing Alone

A design doc does not point at the guide and does not cite an issue number:
write what the pointer would have said. Links between design docs are fine.
Enforced by `tests/test_design_docs_stand_alone.py`.

## Diagrams

Layers, the flow between components, and a sequence across threads are drawn,
as a `mermaid` fence. It renders on the site and on GitHub, diffs as text, and
a tool that never renders it can still read it.

- `flowchart` with subgraphs for structure
- `sequenceDiagram` for protocols
- a `text` fence for a small spatial nesting (boxes inside boxes) when the
  drawing *is* the point

`mkdocs build --strict` does not validate Mermaid syntax. Check a new diagram
in `mkdocs serve` or the GitHub preview.

## Checklist

- [ ] The outline was written in the reply before the edit; every heading in the diff is one of its nodes; `grep -n '^##' docs/design/<page>.md`, read top to bottom, divides on one axis at each level
- [ ] What the design is and how it is realised, as present-state constraints: no parameter lists, no procedure, no measurements, no history
- [ ] No link into `docs/guide/`, no issue number: `uv run pytest tests/test_design_docs_stand_alone.py`
- [ ] Each sentence: one fact, current state, one the reader cannot observe from the docstrings or `docs/guide/`, both open beside the draft; a reason only where a choice was made; every cut a deletion, not a merge
- [ ] Structure, flow and sequences drawn as `mermaid`; every new diagram rendered once
- [ ] `uv run --group docs mkdocs build --strict` passes
