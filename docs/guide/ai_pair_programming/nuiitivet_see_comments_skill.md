# The `nuiitivet-see-comments` skill

```
/nuiitivet-see-comments
```

Run it in chat after you leave
[comment mode](dev_bridge_mcp.md#write-instructions-on-the-app-comment-mode).
The assistant reads the comments you left in the app and does what each one
says — all of them in one turn — then answers by number: `#1 done`,
`#2 refused` and why.

Without the MCP server registered, the skill reads the same comments through
`python -m nuiitivet.dev see-comments`, so nothing else needs setting up.

Without the skill, `see_comments` does the same when the dev bridge
MCP server is registered. "See the comments" does not: an assistant reads that
as code comments or review comments.

## Install

```bash
python -m nuiitivet.skills install
```

That installs every bundled skill, this one included. The Claude Code plugin
does the same, and the
[`nuiitivet-app` install section](nuiitivet_app_skill.md#install) covers
copying one skill by hand — substitute `nuiitivet-see-comments` for the name.

## Next Steps

- [AI pair-programming](index.md) — the section overview.
