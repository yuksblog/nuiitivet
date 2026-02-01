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

## 📦 Release Process

The build, upload to PyPI, and documentation deployment are **automated via GitHub Actions**.

### Procedure

1. **Local Preparation**
    - Update `version` in `pyproject.toml` (e.g., `0.1.2` -> `0.1.3`).
    - Run `uv lock` to update the lock file.
    - Commit and push the changes.

2. **GitHub Release**
    - Go to the [Releases](https://github.com/yuksblog/nuiitivet/releases) page.
    - Click **Draft a new release**.
    - **Choose a tag**: Enter the new version number (e.g., `0.1.3`) and create it.
    - Click the **Generate release notes** button (PR contents will be auto-filled).
    - Review the content and click **Publish release**.

3. **Automated Deployment**
    - GitHub Actions (`release.yml`) is triggered.
    - Package is published to PyPI.
    - GitHub Pages documentation is updated.
