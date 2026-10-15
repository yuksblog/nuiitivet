# The skills

A skill is a bundle of instructions your coding agent loads on its own when
the task calls for it. The features of this section work without them; the
skills are what make the agent use them well. All three are installed in
[Set up](setup.md#2-install-the-skills).

## Have it write idiomatic Nuiitivet

`nuiitivet-app` keeps the agent from writing Nuiitivet with other frameworks'
habits. The API *resembles* Flutter, SwiftUI / Compose and Rx, so left alone
the agent writes valid Python with `setState`, `Padding` / `SizedBox`
wrappers, and `subscribe()` to push a value into a widget. The skill carries
the idioms and a linter for the habits.

## Have it run and check the app itself

`nuiitivet-debug` has the agent run your app under hot reload, read the
running tree, drive it, and check its own change before it answers — instead
of guessing from a screenshot or racing a spinner.

## Have it read your comments and wait for each Send

`nuiitivet-see-comments` has the agent read the comments you
[wrote on the app](comment_mode.md) and answer on each mark. In chat,
`/nuiitivet-see-comments watch` once per session makes it wait for each
**Send**, handle every comment in a turn, and wait again. Without `watch`, it
reads them once.

## Next Steps

- [The dev bridge](dev_bridge.md) — what the agent sees and does in your
  running app, and the commands to drive it yourself.
- [With a coding agent](index.md) — the section overview.
