# Contributing to nuiitivet

Every change starts as an issue and lands on `main` through a pull request.

## Branches

`<type>/<issue>-<short-description>`, the type a commit type below:
`feat/15-add-date-picker`, `fix/23-crash-on-startup`, `release/0.22.0`.

## Implementation

- Type hints everywhere; no duck typing.
- Every public API has a docstring.
- `samples/` imports only the public root, `import nuiitivet.material as nv`,
  the way an app does (`tests/test_public_imports.py`).
- `tests/` imports from the module that defines the symbol,
  `from nuiitivet.layout.column import Column`, so that moving a symbol breaks
  the test that owns it.

A code change comes with its tests in `tests/`, and the checks CI runs pass
locally:

- `uv run pytest`
- `uv run mypy`
- `uv run flake8 src tests samples --max-line-length=120 --extend-ignore=E203`

A change under `docs/` passes:

- `uv run --group docs mkdocs build --strict`

## Commits

Conventional Commits, `type(scope): description`:
`fix(layout): solve overflow in column`.

| Type | Change |
| --- | --- |
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting; no change in meaning |
| `refactor` | Neither a fix nor a feature |
| `perf` | Performance |
| `test` | Tests only |
| `chore` | Build and tooling |
| `release` | Version bump only |

## Pull requests

The title is a release-note line, written like a commit. The label picks the
section (`.github/release.yml`):

| Label | Release notes |
| --- | --- |
| `enhancement` | Features |
| `bug` | Bug Fixes |
| `documentation` | Documentation |
| `refactor`, `chore` | Maintenance |
| `ignore-for-release` | Left out |

`Closes #<issue>` in the body closes the issue on merge.

## Releases

The maintainer bumps the version with `scripts/dev/bump_version.py` and opens
a `release: <version>` PR labelled `ignore-for-release`. Merging it tags,
publishes to PyPI and deploys the documentation (`release.yml`).

## Where a fact lives

Each kind of text about the framework has one job. Write a fact once, in the
lowest row of this table it fits; a row above may link there. The skill column
says how to write that place.

| Place | Carries | Skill (`.claude/skills/`) |
| --- | --- | --- |
| Design doc (`docs/design/`) | The core ideas: what the design is, how it is realised, which alternatives were rejected and why. API and procedure only as far as the design needs them | `design-creator` |
| Guide (`docs/guide/`) | How a user does something and what will surprise them | `guide-creator` |
| MCP server text (`src/nuiitivet/dev/mcp_server.py`) | What the server drives, which question goes to which tool, what each tool returns, the skill names | `nuiitivet-skill-maintainer` |
| Skill (`skills/`) | The agent's procedure and judgement: the order of steps, the choice between tools that could both answer, a rule for a mistake actually made. In `nuiitivet-app`, the Nuiitivet idiom beside the foreign habit it replaces | `nuiitivet-skill-maintainer` |
| Code (`src/`) | The procedure; a docstring what the caller can observe; a comment the *why*, once, at the definition site | `refactor` |
