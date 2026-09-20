---
name: nuiitivet-see-comments
description: Read and act on the comments the user left in the running Nuiitivet app — the numbered marks and typed instructions from comment mode. Use when the user types `see_comments` or "see the comments", or refers to one of those comments by its number, e.g. "fix comment 2", "no. 2 of comment mode is too narrow". Reads the `see_comments` MCP tool, or `python -m nuiitivet.dev see-comments` when that tool is not registered.
user-invocable: true
---

# See the Comments

1. Call the `see_comments` MCP tool. No tool of that name is registered → run
   `python -m nuiitivet.dev see-comments` from the project root.
2. Each comment is the user's instruction to you, written on the widget or
   area they marked. Handle every one in one turn and answer by number:
   `comment 1: done`, `comment 2: refused`, with the reason. A change to make →
   make it. A problem they saw → do not edit yet: enter the nuiitivet-debug
   skill's loop at **See**.
