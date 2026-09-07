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

Guides live in `docs/guide/`, design documents in `docs/design/`. Run
`uv run --group docs mkdocs build --strict` before opening the PR.

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
