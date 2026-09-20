---
name: nuiitivet-debug
description: Run, hot-reload, inspect, drive, and debug a running Nuiitivet app. Covers launching under hot reload (`python -m nuiitivet.dev`) and the dev bridge / MCP server that lets an assistant check and drive the live app (`status`, `describe_tree`, `describe_state`, `see_comments`, `reload_log`, `interaction_log`, `runtime_log`, `screenshot`, `click`, `scroll`, `scroll_into_view`, `type`, `key`, `wait_for`, `profile_start`, `profile_stop`). Use whenever there is a Nuiitivet app to run, verify, or debug — the see → act → verify half of the loop. To *write* the widget code, use the nuiitivet-app skill.
---

# Running & Debugging Nuiitivet Apps

The **nuiitivet-app** skill makes the assistant *write* correct Nuiitivet code.
This skill is the other half: *run* that code under hot reload, then *see* → *act*
→ *verify* against the live app.

## The loop

Once set up, the working loop is:

**edit (hot reload) → see (`status`, then `describe_tree` / `describe_state`) → act
(`click` / `scroll` / `type` / `key`, then `wait_for`) → verify → edit.**

The sections below map to it: a one-time **Setup**, then **Edit / See / Act /
Verify**. The nuiitivet-app skill keeps *edit* producing correct widgets; this
skill keeps *see / act / verify* fast and reliable.

### Where a round starts

What the human handed you decides where you enter the loop.

| The human handed you | Enter at |
| --- | --- |
| A change to make ("make it wider", "move it below the title") | **Edit** |
| A problem they saw ("nothing happens", "the total is wrong after deleting a row") | **See** |
| Comments they left in the running app in comment mode — they type `see_comments`, or refer to one by its number, e.g. "fix comment 2", "no. 2 of comment mode is too narrow" | **See** — each comment is one of the two above |

For a problem, do not edit until you have observed the symptom.

## Setup — before the loop

**Call `status` first.** The human usually has the app open already; `running:
true` means use that process (check `title`), and a second launch would put a
second window on their screen. Launch only on a "no running app" error:

```
python -m nuiitivet.dev run path/to/app.py  # or: run --module pkg.app
python -m nuiitivet.dev run app.py -- --flag value  # args for the app's own entry
```

The app's `sys.argv` is its path plus anything after `--` — the runner's own
arguments never reach it.

No `nuiitivet-dev` tools registered → the same verbs are CLI subcommands:
`python -m nuiitivet.dev describe-tree`, `python -m nuiitivet.dev click --label
Save`. `python -m nuiitivet.dev --help` lists them.

## Edit — change a widget under hot reload

Write or change the widget with the **nuiitivet-app** skill's idioms, then save:
the running window reloads in place while `Observable` state survives — no restart,
no lost state. A broken value survives too: before replaying a reported problem,
drive the app back to where the human's steps began, or restart the runner.
Confirm the reload landed in **Verify**.

## See — check the running app

### Choose the tool

Match the question you have to the one tool that answers it. This is a
**reverse lookup, not a sequence** — reach only for the row you need, never run it
top to bottom. What each tool returns is in its own description.

| The question you have | Tool |
| --- | --- |
| Is the app up and running? | `status` — the cheapest check; call it before any other |
| Is the widget tree built as intended? | `describe_tree` — also where action targets come from |
| Is a control disabled, selected, or focused — and did my `type` land? | `describe_tree`, each node's `state` — not `describe_state` |
| The tree looks wrong — is the state behind it wrong too, or only the display? | `describe_state` |
| My `click` / `scroll` / `type` / `key` had no visible effect — why? | `runtime_log` — before retrying the action |
| Did the last edit reload cleanly, and which file changed? | `reload_log` |
| What did the human do in the app between my turns? | `interaction_log` — before trusting a tree you read earlier |
| The human reported a problem — which steps led to it? | `interaction_log` |
| The human says `see_comments`, "this is wrong", or "look at this part" without naming a widget? | `see_comments` — before guessing from a screenshot |
| `status` reports a `comments` whose `seq` you haven't seen? | `see_comments` |
| A **human reported** a visual problem AND tree + state don't explain it? | first re-check `describe_tree`, then `describe_state`; **only if the cause still isn't clear**, `screenshot` — scoped to the widget they named; the whole frame only when the problem has no widget to name |
| A **human reported** jank or slowness ("this screen stutters", "typing feels heavy")? | `profile_start` → reproduce the interaction (drive it, or ask the human to) → `profile_stop`. Stop it when done: recording slows the frames |

### Read the output

Read these tools' output as *what was recorded or built*, not as *what happened or
is on screen*:

- **`describe_tree` is structure, not rendering or visibility.** Inactive `Deck`
  pages, overlays, and z-order are all listed as-is, so the tree alone can't say
  which one is on screen. Decide the visible page from `describe_state` — a
  `Deck`'s selected index shows up there, joined against the child order in the
  tree.
- **`focused` sits on the node that actually holds the focus, which may be a
  child.** `nv.TextField` delegates to the `EditableText` inside it, so the flag
  lands there and not on the `TextField` you targeted. Search the subtree for it.
- **A node's `rect` can read `0` or stale right after a measurement.** Never
  diagnose a layout bug from a single `rect` value; re-observe after things
  settle.
- **`screenshot(label=...)` crops to the node that displays the text** -- the
  `Text` inside a `Button`, not the `Button`. To frame the whole widget, give it
  a `key` and use `screenshot(key=...)`.

## Act — drive the running app

`click`, `scroll`, `scroll_into_view`, `type`, `key` and `wait_for` do what
their descriptions say. This section holds what the descriptions do not: the
choice between them. Whether an action worked is **Verify**'s question — never
the return alone.

### Name a target

Resolve targets from `describe_tree`, by `key` or `label`. Every widget takes a
stable `key` in its constructor, so give one to the widget you need to drive:

```python
nv.Button("increment", key="increment-btn")
```

Add it on demand and remove it once the need is gone. For a widget built by a
helper you do not control, assign the public attribute: `widget.key = "row"`.

`click` resolves the first depth-first match, so a `label` that repeats can
resolve to the wrong node. Target by `key` when a label repeats; with no `key`
to add, pass the `x` / `y` centre of the node's `rect` — outside a scroll
region only, where `rect` is where the widget is painted.

### Edit the text in a field

`type` only ever inserts. To clear a field, select it all with
`key a modifiers=["accel"]` and then `key backspace`; there is no "set the text"
verb.

### Reach an off-screen target

A "not visible" error is not a bad target: the widget exists and is scrolled
out of its region. Keep the target, call `scroll_into_view` on it, and retry
the action.

### Explore a list

`scroll` is for a list you have not read yet; stop on `at_end`. For a widget you
can name, it is **Reach an off-screen target**.

### Act in a secondary window

An action on a window blocked by a modal child fails with an error naming the
blocking window. Drive the modal child, or close it, instead of retrying.

### Wait for things to settle

- **Waiting on async work:** one `wait_for` before `describe_tree`.
- **Waiting on a *human*** (someone deciding when to click): do **not** set one
  long `timeout`. Keep each `wait_for` short and poll in a loop — re-issue it,
  checking `interaction_log` between tries. The condition is detected only if it
  becomes true while a `wait_for` call is running, and one long call blocks the
  whole turn.

## Verify — confirm the change

Don't trust a green return or a single number; confirm against the live app.

- **The edit landed.** `reload_log` shows a `success` outcome with your file in
  `changed`. An `error` outcome means the save didn't compile and the live UI is
  stale — fix and re-save before reading anything else. `inert_windows` on a
  `success` means no edit can reach those windows: their root is a widget
  instance, which is rule 6 of the **nuiitivet-app** skill.
- **No new error appeared — check `runtime_log`, not `error_count`.** `error_count`
  (from `status`) is cumulative and a green build does not reset it, so a clean
  `last_reload: success` can still report failures from *before* your fix. Instead,
  note the newest `runtime_log` seq before you edit; after the reload, check whether
  any ERROR with a *higher* seq appeared. (`runtime_log` and `reload_log` seqs are
  separate counters — don't compare across them.)
- **The effect happened, not just the return.** A `{"clicked": …}` return is not
  proof the handler fired (a `{"scrolled": …}` with `handled: false` is not even
  proof anything moved). Re-observe `describe_tree` / `describe_state` (after
  `wait_for` settles any async work) and confirm the state actually changed.
