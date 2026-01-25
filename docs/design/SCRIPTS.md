# Scripts layout

This document describes the organization and policies regarding scripts used in the nuiitivet project.

## Directory map

- `scripts/debug/`
  - Local debugging and visualization.
  - Can be invasive (monkeypatches, ad-hoc prints).

- `scripts/investigation/`
  - One-off probes and measurements.
  - Short-lived by design.

- `scripts/dev/format/`
  - Source rewriting/formatting helpers.

- `scripts/dev/repo/`
  - Repository maintenance scripts (AST rewrites, scans, patch generators).

- `scripts/vendor/`
  - Sync scripts that update vendored assets committed into the repo.

## CI policy

- CI should not mutate the repository.
- Prefer checks that validate generated files are up-to-date (fail if diff),
  rather than re-fetching remote assets.
- Network-dependent updates belong in manual workflows (e.g. `workflow_dispatch`) or local runs.
