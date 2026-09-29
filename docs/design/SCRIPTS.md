# Scripts

`scripts/` holds code that is not the framework and not a test, sorted by
how long it is meant to live and what it is allowed to touch:

| Directory | Holds | May |
| --- | --- | --- |
| `scripts/debug/` | local debugging and visualisation | be invasive: monkeypatches, ad-hoc prints |
| `scripts/investigation/` | one-off probes and measurements | be deleted once the question is answered |
| `scripts/dev/` | development support: version bump, MCP launcher, `format/` source rewriters, `repo/` maintenance (AST rewrites, scans, patch generators) | rewrite the tree, by hand |
| `scripts/docs/` | documentation rendering: layout images, the README GIF | regenerate committed assets |
| `scripts/vendor/` | sync scripts that update vendored assets committed into the repo | fetch from the network |

CI never mutates the repository. A check validates that a generated file is
up to date and fails on a diff, rather than regenerating it; a
network-dependent update runs by hand or from a `workflow_dispatch` workflow,
because a CI run that re-fetches a remote asset can pass or fail on the
remote's state rather than on the change under review.
