---
name: nuiitivet-see-comments
description: Read and act on the comments the user left in the running Nuiitivet app — the numbered marks and typed instructions from comment mode — answer each on its mark, and wait for the next Send. Use when the user types `see_comments` or "see the comments", refers to one of those comments by its number, e.g. "fix comment 2", "no. 2 of comment mode is too narrow", or asks to watch (`/nuiitivet-see-comments watch`). Reads the `see_comments` MCP tool, answers with `answer_comments` and waits with `wait_for_comments`, or `python -m nuiitivet.dev see-comments` / `answer-comments` / `wait-comments` when those tools are not registered.
user-invocable: true
---

# See the Comments

1. Call the `see_comments` MCP tool. No tool of that name is registered → run
   `python -m nuiitivet.dev see-comments` from the project root. Keep its
   `sent`: it is the `since` of the next wait.
2. The comments to act on are the ones with `awaiting: true`: sent, and not
   answered yet. The others the user is still writing; leave them. Each
   comment is a thread on the widget or area the user marked: their lines and
   your earlier answers, in order. The newest human line is the instruction.
   A change to make → make it. A problem they saw → do not edit yet: enter the
   nuiitivet-debug skill's loop at **See**, and answer when the loop ends.
3. Answer every awaiting comment through `answer_comments` in the same turn, one entry
   per comment: `{"index": 2, "outcome": "done", "text": "widened to 240"}`.
   `done` with what you did, `refused` with the reason, `question` with the
   question itself; `text` is one short line. No tool of that name is
   registered → `python -m nuiitivet.dev answer-comments 2 done "widened to 240"`,
   once per comment. The answer appears on the mark in the app, which is where
   the user reads it; a `question` waits there for their reply, which comes
   back in that comment's thread on their next Send.
4. One line in chat: how many comments were answered, and nothing else that is
   already on a mark.
5. Watching (`/nuiitivet-see-comments watch`): run steps 1 to 4 once at the
   start, since a Send may have come in before the watch, then go back to
   waiting after step 4, every time. Only the user ends the watch. The user
   presses **Send** in the app; nothing else, leaving the mode included,
   counts as a hand-over. Pass the last `sent` you saw as `since`, so a Send
   that came in while you were answering is not missed. How to wait, by what
   the host offers:
   - A background watch that notifies per stdout line (Claude Code: `Monitor`)
     → run `python -m nuiitivet.dev wait-comments` under it, with the longest
     timeout the watch allows, and re-arm it when it expires. Each line it
     prints is a Send: steps 1 to 4, then wait on. Nothing runs between Sends,
     and the user can still use chat.
   - No such watch → call `wait_for_comments` from a subagent, so the main
     agent is not blocked; it returns `satisfied: false` on its timeout, and
     the subagent calls it again.
   - Neither → call `wait_for_comments` directly and accept that chat waits
     with it.
