# Contributing to nuiitivet

This document outlines the development workflow, branching strategy, and release procedures for nuiitivet.

## 🛠 Development Workflow

All changes start with an **Issue** and are integrated into the `main` branch via a **Pull Request (PR)**.

1. **Create Issue**: Define the task for a new feature or bug fix.
2. **Create Branch**: Create a working branch corresponding to the Issue.
3. **Coding & Commit**: Commit changes following Conventional Commits.
4. **Pull Request**: Create a PR targeting the `main` branch.
5. **Merge**: Merge after review (this will be the source for release notes).

---

## 🌿 Branching Strategy

Branch names should indicate the type of work, issue number, and a brief description.

### Naming Convention

`prefix/issue-number-short-description`

| Prefix | Usage | Example |
| :--- | :--- | :--- |
| `feat/` | New features | `feat/15-add-date-picker` |
| `fix/` | Bug fixes | `fix/23-crash-on-startup` |
| `refactor/` | Refactoring | `refactor/optimize-rendering` |
| `docs/` | Documentation updates | `docs/update-readme` |
| `chore/` | Build settings or tools | `chore/update-dependencies` |
| `release/` | Version bumps | `release/0.22.0` |

---

## 📝 Commit Convention

Commit messages affect the quality of auto-generated release notes, so please follow **Conventional Commits**.

### Format

`type(scope): description`

### Types

- **feat**: New features
- **fix**: Bug fixes
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code (white-space, formatting, etc)
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **perf**: A code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **chore**: Changes to the build process or auxiliary tools and libraries such as documentation generation
- **release**: A version bump, and nothing else. Merging it cuts the release

### Examples

- `feat(button): add proper disabled state styling`
- `fix(layout): solve overflow issue in column`

---

## 🚀 Pull Request & Release Notes

To leverage GitHub's automated release notes generation, please follow these rules when creating a PR.

### 1. Title

The PR title becomes a line item in the release notes. Please describe it clearly.

- ❌ `fix layout`
- ⭕ `fix(layout): Fix overlapping elements bug in Column widget`

### 2. Labels (Important)

By assigning appropriate labels to the PR, it will be automatically categorized in the release notes.

| Implementation | Label (GitHub) | Release Note Category |
| :--- | :--- | :--- |
| New Feature | `enhancement` | 🚀 Features |
| Bug Fix | `bug` | 🐛 Bug Fixes |
| Documentation | `documentation` | 📝 Documentation |
| Others | `refactor`, `chore`, etc. | 🧰 Maintenance |

> **Note**: If `refactor` or `chore` labels do not exist in GitHub, please create them.

### 3. Auto-close Issues

If you write `Closes #IssueNumber` in the PR description, the linked Issue will be automatically closed when merged.

---

## 📚 Documentation

Guides live in `docs/guide/`, design documents in `docs/design/`. The text an
AI assistant reads lives in the published skills (`skills/`) and in the dev
bridge MCP server (`src/nuiitivet/dev/mcp_server.py`). Run
`uv run --group docs mkdocs build --strict` before opening the PR.

### What goes where

Each kind of text has one job, and a fact lives in the place whose job it is.
When a passage would fit two of them, it belongs in the lower one and the
upper one links or stays silent.

| Place | Carries | Leaves out |
| --- | --- | --- |
| Design doc (`docs/design/`) | The framework's core ideas: what the design is, how it is realised, and the alternatives that were rejected and why. API and procedure only as far as the design needs them to be understood | Parameter lists, step-by-step mechanics, measurements, the story of how a rule was found |
| Guide (`docs/guide/`) | How a user does something and what will surprise them | Why the API is shaped that way; a restatement of what a skill tells the assistant |
| MCP server instructions | What the server drives, a one-clause map of which question goes to which tool, and the names of the skills | Procedure and judgement; the details of any one tool |
| Skill (`skills/`) | The assistant's procedure and judgement: the order of steps, the choice between tools that could both answer, a rule for a mistake that was actually made. In `nuiitivet-app`, the Nuiitivet idiom next to the habit from another framework it replaces | What the human does, what a tool returns, a precaution nobody has hit |
| MCP tool description | What the tool returns and when to call it | Field-by-field walkthroughs, procedures, anything the returned JSON already shows |
| Docstring | What the caller can observe: behaviour, timing, constraints | Mechanism and rationale |
| Code | The procedure itself; a comment carries only the *why*, once, at the definition site | Anything the code already says |

A design doc that grows past its name is the usual symptom: it has started
carrying procedure or API reference. Move the surplus down, not into a bigger
doc.

**The assistant's text assumes the skills are installed.** The skill and the
two MCP rows are read by an AI assistant, not a person. The framework is used
with its skills installed, so a tool description does not stand in for a
missing skill. An MCP host may cut what it is sent — Claude Code cuts the
server instructions and each tool description at 2048 characters — so a text
that runs long loses its end, without an error.

**Draw the important structure.** A design doc that describes layers, the flow
between components, or a sequence across threads shows it as a diagram, and
the diagram is a `mermaid` fence: it renders on the site and on GitHub, it
diffs as text, and it is readable by a tool that never renders it. Prefer a
`flowchart` with subgraphs for structure and a `sequenceDiagram` for
protocols; keep a small spatial nesting (boxes inside boxes) as a `text`
fence when the drawing *is* the point. `mkdocs build --strict` does not
validate Mermaid syntax, so check a new diagram in `mkdocs serve` or the
GitHub preview.

### Linking between guide pages

Cross-links are the part of a guide that rots. With N sibling pages covering
interchangeable tools, keeping "see also" lists honest is an N×N job, and every
page added makes it worse. Three rules keep it linear:

1. **"Next Steps" is the reading order, not a see-also list.** It carries the
   next page in the section's `index.md` order, plus the section overview —
   nothing else. A page the reader has already passed does not belong there.
2. **A body link must earn its sentence.** Link sideways where the page stops
   short and names what continues, or where it leans on a specific section
   elsewhere (link the anchor, not the page). Do not add the reciprocal link
   back just because the other page points here — a standalone "Related" or
   "See also" callout added for symmetry is what these rules exist to prevent.
3. **When both sides need routing, route through a hub.** A page that answers
   "which of these do I use?" — `docs/guide/concurrency.md` is the worked
   example — is linked from the section index, and each tool page links up to it
   at most once. That is N edges instead of N².

### Writing a skill

The reader is an assistant. It does not fill a gap from context: it invents
something to fill it, or follows whichever fragment it retrieved.

- **A new feature goes into the skill's outline, not into a section appended
  for it.** An appended section ends up restating the skill. Sibling headings
  divide their parent on one axis, with no gap and no overlap.
- **One rule, one canonical statement.** The section that owns a fact states
  it; other sections name that section.
- **Every prohibition names its replacement, adjacent.** "Do not `setState`" on
  its own buys a different wrong answer.
- **No hedging.** "Generally", "prefer", "you may want to" hand the decision
  back. State the rule, or the condition that selects between two rules.
- **Real symbols, not descriptions.** `nv.ComposableWidget`, never "the
  composable base class".
- **No unresolved references.** "As above" does not survive being read as a
  fragment. Name the file or the heading.
- **Wrong code is labelled, and sits next to the right code.** An unlabelled
  bad snippet gets copied.
- **No external URLs, and no links into `docs/guide/`.** A skill is
  self-contained; knowledge it lacks is folded into it.
- **Handover between skills runs one way**: from the skill the user invokes to
  the skill that carries the loop, never back.

### Adding a page

Add it to the `nav` in `mkdocs.yml` and to the section `index.md` reading order,
then fix the **Next Steps** of the page it now follows so the chain still reads
in order.

---

## 📦 Release Process

Releases are cut by the maintainer, not by contributors: merging a
`release: <version>` PR — the version bumped with
`scripts/dev/bump_version.py` and the PR labelled `ignore-for-release` — is what
tags, publishes to PyPI, and deploys the documentation, all in `release.yml`.
