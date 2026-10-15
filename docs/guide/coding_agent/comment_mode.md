# Comment mode

Telling an agent *where* is often the hard part of telling it what to do.
Comment mode puts the instruction on the app itself.

## 1. Have the agent answer your comments

The agent answers on the marks either way. A watch answers every Send of the
session; a read answers what you have sent so far.

### Watch for every Send

In chat, once per session: `/nuiitivet-see-comments watch`. From then on the
agent answers each **Send** you make in the app; no chat message is needed.

### Read once

`/nuiitivet-see-comments` in chat reads and answers what you have sent, once.
Without the skill [installed](setup.md#2-install-the-skills), `see_comments`
does the same.

## 2. Enter the mode

Press `Ctrl+Shift+C` (`Cmd+Shift+C` on macOS). The mode's name and `H help`
show at the centre for a moment.

## 3. Mark the place

Hover, and the widget under the cursor gets amber corner brackets and a
caption naming it: the one a click would mark. Click, and a numbered badge
sits at its corner from then on.

### Mark an empty area

Drag instead of clicking to mark an **area** — a gap, a misaligned band,
anywhere with no widget to name.

### Aim at a covered or tiny widget

When the widget you mean is covered by its children or too small to aim at,
walk to it from the keys. `W` / `S` move the choice up to its parent and back
down. `A` / `D` move it along to the widget beside it. `Enter` or a click
then marks it.

## 4. Write the instruction

A field opens on the mark. Type what you want done and press `Enter`.

### Leave the mark bare and name it in chat

A mark with no text is fine. Name it by its number in chat.

### Report a problem instead of a change

Write what went wrong, right after it happens. The agent reads the clicks and
keys you made just before, and reproduces the problem before fixing it.

### Change or clear what you wrote

Before the agent answers, click the marked widget or its badge: the field
opens again on your text. `Enter` with the text emptied keeps just the
number. `Esc` closes the field without a change. On a mark you just made
with nothing written yet, `Esc` removes the mark too.

## 5. Send to the agent

Mark as many places as you like, then press `Ctrl+Enter`, or the **Send**
button at the window's bottom-right. The button hides below the window's edge
with a sliver showing. Bring the pointer to the sliver and it stands up. What
goes out is the mark and your words on it. Nothing you type elsewhere in the
app ever does.

## 6. Read the answer

After a Send, a grey disc with an hourglass joins the number of every mark
the agent has not answered yet. Stay in the mode: the hourglass turns into a
coloured disc, green with a check mark for `done`, red with a cross for
`refused`, blue with a question mark for a `question` to you. Hover the badge
to read the thread under it: your lines and the agent's, each led by an icon
for who wrote it. A thread taller than the window shows its newest lines and
counts the rest.

## 7. Act on the answer

A `question`, or a `refused` you disagree with, gets a reply. A `done`, or a
refusal you accept, gets removed.

### Reply on a mark

Click the mark: the field opens empty for your reply. Write and send as
before. The agent reads the whole thread.

### Remove a mark

`Delete` or `Backspace` removes the mark under the cursor, on its widget or on
its badge. `Ctrl+Backspace` removes every mark, sent ones included. `Ctrl+Z`
brings them back.

## 8. Leave

Press `Esc` when you want the app back. The marks go off the screen but stay,
sent or not, and come back with the mode. The line at the centre says
`unsent comments` if you left something the agent has not seen.

## Every gesture

| Gesture | What it does |
| --- | --- |
| `Ctrl+Shift+C` | Enter comment mode (`Cmd+Shift+C` on macOS — either accelerator works throughout). |
| Hold `H` | Show every gesture of this mode while the key is down. |
| Hover | The widget under the cursor gets amber corner brackets and a caption naming it: the one a click would mark. |
| `W` / `S`, `A` / `D` | Move that choice up to its parent and back down, or along to the widget beside it. `Enter` or a click then marks it. |
| Click | Mark the widget under the cursor; a field opens on the mark. On a marked widget, or on its numbered badge, the field opens again instead: on your text, to change or clear it, or empty once the agent has answered, to reply. |
| Drag | Mark an area instead. The field opens the same way. |
| In the field | `Enter` keeps the text (empty keeps just the number); `Ctrl+Enter` keeps it and sends; `Shift+Enter` breaks the line; `Esc` closes the field, and removes a new mark with nothing written (`Ctrl+Z` brings it back). `Shift+←/→` selects, `Ctrl+A/C/X/V` (`Cmd` on macOS) select all, copy, cut and paste. A click keeps the text and then does what it would have done anyway. |
| `Ctrl+Enter`, or **Send**, the button at the bottom-right | Send your comments to the agent. The button stands up when the pointer reaches its sliver at the window's edge. A click there also keeps the open field. |
| The badge | After **Send**, a grey disc with an hourglass until the agent answers; then green with a check mark for done, red with a cross for refused, blue with a question mark for a question to you. |
| Hover a mark's numbered badge | Read its thread under the badge, each line led by an icon for who wrote it; a thread taller than the window shows its newest lines and counts the rest. |
| `Delete` / `Backspace` | Remove the mark under the cursor, on its widget or on its badge. `Ctrl+Z` brings it back. |
| `Ctrl+Z` / `Ctrl+Shift+Z` | Undo and redo what you did since you last sent — a mark, an unmark, a text. The same keys as layout edit mode. |
| `Ctrl+Backspace` | Remove every mark, sent ones included. `Ctrl+Z` brings them back. |
| `Esc` | Leave. The marks go off the screen but stay, sent or not; enter again and they are back as you left them. |
| `Ctrl+Shift+E` | Switch to [layout edit mode](layout_edit_mode.md), your marks kept. |

## Next Steps

- [Layout edit mode](layout_edit_mode.md) — fix a size, an order or an
  alignment yourself, by dragging.
- [With a coding agent](index.md) — the section overview.
