---
name: design-creator
description: Create or update a design document in docs/design/: what a design doc carries and leaves out, standing alone, diagrams, the checklist.
---

# Design Creator

Creating and updating design documents in `docs/design/`. The pages are built
into the site and reached by link, not from the sidebar.

## What to Write

**The reader builds or changes the framework; they do not use it.** A design
doc carries the core ideas: what the design is, how it is realised, and the
alternatives that were rejected and why. API and procedure appear only as far
as the design needs them.

Cut on sight, and move it down to the place whose job it is:

- parameter lists and signatures — the docstring
- step-by-step mechanics and measurements — the guide, or the code
- the story of how a rule was found — nowhere; state the rule as present-state design

A design doc that grows past its name has started carrying procedure or API
reference. Move the surplus down, not into a bigger doc.

**A rejected alternative is one the reader would reach for**, stated as a
present-state constraint: "`"50%"` raises `ValueError`; accepting it as a
weight was rejected because it reads as a fraction of the parent." An
alternative nobody would choose is not written. "We tried X and went back" is
history; it goes to the issue.

**A sentence the reader can picture beats an exact one.** "The field ends up
reformatting itself under the user's cursor" lands; "two observables describing
one thing" does not. Reach for the exact form only where the picture would be
wrong.

**Short sentences, dense from the first line to the last.** Each sentence
carries one fact the reader does not have. A fact is stated once; it is
repeated only where the two places are far apart.

**Sibling headings divide their parent on one axis**, with no gap and no
overlap. Check the whole page, not only the section touched.

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

- [ ] Core ideas, realisation, and the alternatives a reader would reach for, each as a present-state constraint — no parameter lists, no procedure, no measurements, no history
- [ ] No link into `docs/guide/`, no issue number: `uv run pytest tests/test_design_docs_stand_alone.py`
- [ ] Short sentences, one fact each, dense throughout; a fact repeated only where two places are far apart
- [ ] Sibling headings divide their parent on one axis, no gap, no overlap — checked on the whole page, not only the section touched
- [ ] Structure, flow and sequences drawn as `mermaid`; every new diagram rendered once
- [ ] `uv run --group docs mkdocs build --strict` passes
