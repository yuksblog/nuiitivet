---
name: nuiitivet-see-comments
description: Read and act on the comments the user left in the running Nuiitivet app — the numbered marks and typed instructions from comment mode — and answer each on its mark. Use when the user types `see_comments` or "see the comments", or refers to one of those comments by its number, e.g. "fix comment 2", "no. 2 of comment mode is too narrow". Reads the `see_comments` MCP tool and answers with `answer_comments`, or `python -m nuiitivet.dev see-comments` / `answer-comments` when those tools are not registered.
user-invocable: true
---

# See the Comments

1. Call the `see_comments` MCP tool. No tool of that name is registered → run
   `python -m nuiitivet.dev see-comments` from the project root.
2. Each comment is a thread on the widget or area the user marked: their
   lines and your earlier answers, in order. The newest human line is the
   instruction. A change to make → make it. A problem they saw → do not edit
   yet: enter the nuiitivet-debug skill's loop at **See**, and answer when the
   loop ends.
3. Answer every comment through `answer_comments` in the same turn, one entry
   per comment: `{"index": 2, "outcome": "done", "text": "widened to 240"}`.
   `done` with what you did, `refused` with the reason, `question` with the
   question itself; `text` is one short line. No tool of that name is
   registered → `python -m nuiitivet.dev answer-comments 2 done "widened to 240"`,
   once per comment. The answer appears on the mark in the app, which is where
   the user reads it; a `question` waits there for their reply, which comes
   back in that comment's thread.
4. One line in chat: how many comments were answered, and nothing else that is
   already on a mark.
