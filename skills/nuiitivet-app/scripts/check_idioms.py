#!/usr/bin/env python3
"""check_idioms.py — warn about foreign-framework idioms in Nuiitivet code.

Nuiitivet borrows surface ideas from Flutter, React, Rx, and Compose, so leaked
idioms from those frameworks are almost always *valid Python* — a plain syntax
check won't catch them. This linter looks for high-confidence foreign signatures
that have no legitimate use in Nuiitivet, and points at the correct idiom.

It only WARNS. It never edits code. Fix each finding by hand using the pointer
and the skill's references/translation.md.

Deliberately NOT flagged (legitimate in Nuiitivet, would be noisy):
  - `.of(self)`           -> Navigator.of / Overlay.of are real APIs
  - `.subscribe(`         -> valid for side effects; only pushing into UI is bad
  - `Padding` / `SizedBox`-> flagged only via the Flutter constructor shapes below
  - `.cancel(`            -> too common; only the foreign cancellation type names hit

Usage:
  python check_idioms.py <file-or-dir> [<file-or-dir> ...]

Exit code: 0 if clean, 1 if any findings (so it can gate CI if desired).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Each rule: (compiled_regex, framework, why + the Nuiitivet fix)
RULES: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"\bStateless?Widget\b|\bStatefulWidget\b"), "Flutter",
     "Subclass nv.ComposableWidget and define build(self)."),
    (re.compile(r"\bcreateState\b|\binitState\b"), "Flutter",
     "No state lifecycle overrides; create Observables in __init__, and put setup "
     "that needs the tree (X.of(self), async loading) in an on_mount() override."),
    (re.compile(r"\bonAppear\b|\bonDisappear\b|\bon_appear\b|\bon_disappear\b"), "SwiftUI",
     "No on_appear/on_disappear exists. SwiftUI's onAppear is tree insertion, which is "
     "on_mount()/on_unmount(). Nothing fires when a route merely gets covered: pause and "
     "resume from the caller side instead."),
    (re.compile(r"\bRouteAware\b|\bdidPushNext\b|\bdidPopNext\b"), "Flutter",
     "No route-visibility callbacks: a covered route stays mounted and nothing fires. "
     "Pause/resume from the code calling Navigator.of(self).push(...), or from the "
     "Observable behind a nv.Deck index."),
    (re.compile(r"\bLaunchedEffect\b|\bDisposableEffect\b|\brememberCoroutineScope\b"), "Jetpack Compose",
     "Run-once setup: override on_mount() (runs once per instance; a rebuild replaces the "
     "built subtree, not the host). From inside build(), use nv.on_mount(cb) plus a flag "
     "owned outside the rebuilt subtree."),
    (re.compile(r"\bdef\s+build\s*\(\s*self\s*,\s*context\b"), "Flutter",
     "build takes no context: `def build(self):`."),
    (re.compile(r"\bsetState\b"), "Flutter/React",
     "Assign to an Observable: `self.x.value = ...` — the UI rebinds itself."),
    (re.compile(r"\buseState\b|\buseEffect\b|\buseMemo\b|\buseRef\b|\buseCallback\b"), "React",
     "Use nv.Observable for state; derive with combine().compute() / map()."),
    (re.compile(r"\buseSelector\b|\buseDispatch\b|\bConsumerWidget\b|\bref\.watch\b"), "Redux/Riverpod",
     "Bind an Observable directly into the widget; no store/provider hooks."),
    (re.compile(r"\bEdgeInsets\b"), "Flutter",
     "Spacing is a parameter: `padding=12` on the widget."),
    (re.compile(r"\bSizedBox\s*\("), "Flutter",
     "Size is a parameter: `width=`, `height=` on the widget (or gap= for spacing)."),
    (re.compile(r"\bPadding\s*\(\s*padding\b"), "Flutter",
     "Padding is a parameter: `padding=` on the widget, not a wrapper."),
    (re.compile(r"\b(?:alignment|main_alignment|cross_alignment)\s*=\s*"
                r"[\"'](?:stretch|flex-start|flex-end|baseline|fill)[\"']"), "CSS flexbox",
     "alignment is positioning-only. For stretch/fill set the child's size "
     "(width=\"wt\"); use start/center/end, not flex-start/flex-end."),
    (re.compile(r"(?:width|height|length|size)\s*=\s*[\"'][0-9.]+%[\"']"), "CSS/removed spelling",
     "Percentage sizing does not exist: a size is fixed (a number), \"auto\", or a "
     "weight (\"wt\" / \"wt2\") that shares the leftover space. \"100%\" was never a "
     "fraction of the parent - write \"wt\"."),
    (re.compile(r"\b(?:Navigator|Overlay)\.root\s*\(\s*\)|\b(?:Navigator|Overlay)\.set_root\b"), "removed API",
     "Navigator.root() / Overlay.root() are gone: a process-global root cannot "
     "say which App it belongs to. Resolve from a mounted widget instead - "
     "nv.Navigator.of(self) / nv.Overlay.of(self) return the nearest enclosing one and "
     "fall back to the App's; add root=True to force the App's."),
    (re.compile(r"\bSizing\.flex\s*\("), "removed API",
     "Sizing.flex is gone. Write the string form: width=\"wt\" (or \"wt2\" for an "
     "uneven share); nv.Sizing.weight(n) exists but is not the idiom."),
    (re.compile(r"\bLayoutBuilder\s*\(|\bMediaQuery\b"), "Flutter",
     "Measure the widget itself: X.modifier(nv.on_size_changed(cb)) reports its "
     "nv.Size after layout. Use nv.Geometry(child, width=\"wt\") + "
     "nv.Geometry.of(self).size only when a *subtree* must read an ancestor's box."),
    (re.compile(r"\bGeometryReader\b|\bBoxWithConstraints\b"), "SwiftUI/Compose",
     "Attach nv.on_size_changed(cb) to the filling widget you want measured; wrap "
     "in nv.Geometry only when descendants must read that box."),
    (re.compile(r"\bdef\s+set_layout_rect\b"), "layout-hook workaround",
     "Do not override layout to publish a size: nv.on_size_changed(cb) reports a "
     "widget's own measured size, and nv.Geometry publishes one to a subtree."),
    (re.compile(r"\bMaterialPageRoute\b"), "Flutter",
     "nv.Navigator.of(self).push(Screen()) or Intent-based routing; no MaterialPageRoute."),
    (re.compile(r"\bshowDialog\s*\("), "Flutter",
     "await nv.Overlay.of(self).dialog(nv.BasicDialog(...)); close with overlay.close(v)."),
    (re.compile(r"\bScaffoldMessenger\b"), "Flutter",
     "nv.Overlay.of(self).snackbar(\"...\")."),
    (re.compile(r"\b(?:from|import)\s+(?:plyer|win10toast|win11toast|notify2|desktop_notifier|pync)\b"),
     "external notification libs",
     "OS notifications are built in: nv.Desktop.notify(title, body) — fire-and-forget, "
     "never raises, safe from any thread. In-window feedback is "
     "nv.Overlay.of(self).snackbar(...)."),
    (re.compile(r"\bfiledialog\b|\bask(?:openfilename|openfilenames|saveasfilename|directory)\s*\(|"
                r"\bQFileDialog\b|\bNS(?:Open|Save)Panel\b"),
     "foreign file-dialog toolkits",
     "Native dialogs are built in: path = await nv.FileDialog.open_file(file_types=[...]) "
     "— coroutine, call from an async handler. Cancel is None (open_files: []); also "
     "save_file / open_directory. nv.FileDialogError when the dialog cannot be shown."),
    (re.compile(r"\b(?:from|import)\s+(?:pystray|infi\.systray)\b|\bpystray\.Icon\b"),
     "external tray-icon libs",
     "The system tray is built in: nv.App(win, tray=nv.TrayIcon(icon=..., tooltip=..., "
     "menu=[nv.MenuEntry(...)])) — the menu reuses MenuEntry, and tray.installed "
     "(Observable[bool]) reports whether the icon actually shows. Resident app: "
     "exit_policy=nv.ExitPolicy.EXPLICIT + Window(close_action=tray.installed.map(...)) "
     "+ win.hide()/show(). Never import pystray directly."),
    (re.compile(r"\bQFontDatabase\b|\baddApplicationFont\b|\btkinter\.font\b"),
     "foreign font loading",
     "Bundled fonts are built in: nv.Fonts.register(\"assets/fonts/X.ttf\", "
     "family_name=\"X\") once at startup, then font_family=\"X\" wherever a "
     "font_family is accepted. Default family: nv.Fonts.set_default_family(...)."),
    (re.compile(r"\bnv\.(?:register_font|set_default_font_family)\s*\("), "nuiitivet (old API)",
     "Font configuration lives on the nv.Fonts namespace: nv.Fonts.register(path, "
     "family_name=...) / nv.Fonts.set_default_family(...)."),
    (re.compile(r"\bnv\.(?:get_clock|set_clock)\s*\("), "nuiitivet (old API)",
     "The clock seam lives on the nv.Clocks namespace: nv.Clocks.get() / "
     "nv.Clocks.set(clock)."),
    (re.compile(r"\bTextEditingController\b"), "Flutter",
     "No controller object: bind an Observable as the field's value, "
     "nv.TextField(value=obs). Set the text with obs.value = ..."),
    (re.compile(r"\bonEditingComplete\b"), "Flutter",
     "Finishing a value on blur is nv.TextField(on_focus_change=fn), called as "
     "(focused, source). on_submit is Enter only and never fires on blur."),
    (re.compile(r"\bshowSearch\s*\(|\bSearchDelegate\b|\bSearchAnchor\b"), "Flutter",
     "No full-screen search widget: put nv.SearchBar(obs, placeholder=...) in a screen "
     "you lay out yourself, or use nv.DockedSearchBar(obs, content=widget) for a "
     "dropdown. width names the box; the bar is inset inside it."),
    (re.compile(r"\bpushReplacement\b|\bpushNamed\b|\bpopUntil\b"), "Flutter",
     "No push_replacement / pop_until in Nuiitivet: push a widget or Intent with "
     "Navigator.of(self).push(...); go back with Navigator.of(self).pop()."),
    (re.compile(r"\brunApp\s*\(|\bMaterialApp\s*\("), "Flutter",
     "nv.App(nv.Window(content=build_root)).run() — pass a factory for hot reload."),
    (re.compile(r"\bApp\(\s*content\s*="), "nuiitivet (old API)",
     "App takes its main Window: nv.App(nv.Window(content=..., title=...)). Window "
     "keywords (title, width, menu, ...) live on nv.Window; App keeps theme= and "
     "exit_policy= only."),
    (re.compile(r"\bBuildContext\b"), "Flutter",
     "No BuildContext type; context is passed where needed without annotation."),
    (re.compile(r"@Composable\b"), "Jetpack Compose",
     "Define a ComposableWidget subclass with build(self)."),
    (re.compile(r"\bcomputed\s*\(|\bobservable\s*\(\s*\)|\bmakeAutoObservable\b"), "MobX/Vue",
     "Derived state: a.combine(b).compute(lambda a, b: ...)."),
    (re.compile(r"\bCancellationTokenSource\b|\bCancellationToken\b|\bAbortController\b"), ".NET/JS",
     "No cancellation primitive of that shape. If the work is a function of an Observable's "
     "value, use source.switch_map(fn, initial=...) — it supersedes the previous run and hands "
     "fn an nv.CancelToken. Otherwise create a threading.Event per run, pass it to the worker, "
     "and check cancel.is_set() in its loop; a reused Event that gets clear()ed lets a "
     "superseded run resume."),
    # Foreign spellings of switch_map. The latest-wins operator exists under that
    # name, so the fix is a rename; the flattening operators below do not exist at
    # all, which is why they are named separately rather than pointed at it.
    (re.compile(r"\.(?:switchMap|flatMapLatest|switchLatest|collectLatest)\s*\("), "Rx/Kotlin",
     "Nuiitivet spells this switch_map(fn, initial=...) — fn takes (value, cancel) and initial "
     "is required and keyword-only."),
    (re.compile(r"\.(?:exhaustMap|concatMap|mergeMap|flatMap)\s*\("), "Rx",
     "Only the latest-wins variant exists: switch_map(fn, initial=...). There is no "
     "exhaust/concat/merge flattening — a derived Observable holds one value, not a queue of "
     "in-flight runs."),
    # switch_map's fn takes (value, cancel). A one-parameter lambda is the natural
    # thing to write coming from map(), and fails only once a run actually starts.
    (re.compile(r"\.switch_map\s*\(\s*lambda\s+[A-Za-z_]\w*\s*:"), "map habit",
     "switch_map's fn takes two arguments: (value, cancel). Write "
     "switch_map(lambda value, cancel: ..., initial=...) — the token is cooperative, so "
     "ignoring it is fine, but it is always passed."),
    # Three-state async wrapper types. Rejected deliberately: a wrapper in the
    # value position forces every downstream operator and binding to unwrap it.
    (re.compile(r"\bAsyncValue\b|\bRemoteData\b|\bAsyncSnapshot\b"), "Flutter/Elm",
     "No loading/error wrapper type around the value. switch_map returns a plain Observable; "
     "put failure in your own result type (SearchOutcome(items=..., error=...)) so one value "
     "carries both and downstream map/filter/combine need no unwrapping."),
    # Bare-statement subscribe on a debounce/throttle/filter chain. In Rx the stream
    # is owned by the source, so dropping the subscription handle is normal; here the
    # chain is owned by whoever holds it, so this silently never fires. Excludes
    # lines that assign the result, or pass it to "bind(" (held by the widget).
    # The exclusion tests for an assignment *target* rather than for any "=" at
    # all: `filter` always carries `initial=`, so a bare "=" test would exempt
    # every filter chain — the one operator whose seed makes "=" unavoidable.
    # Both guards are anchored at "^" and swallow the indentation themselves: a
    # leading "^\s*" outside them would backtrack to a shorter run of spaces and
    # slip past a guard that had already matched.
    (re.compile(r"^(?![ \t]*[\w.\[\]'\"]+\s*=[^=])(?!.*\bbind\s*\().*"
                r"\.(?:debounce|throttle|filter)\s*\([^()]*\)\s*\.\s*subscribe\s*\("), "Rx habit",
     "Hold what you derive: debounce/throttle/filter returns a new Observable that is "
     "collected unless something holds it, so this never fires. Name it (self.results = ...), "
     "or keep the Disposable: self.bind(source.debounce(0.3).subscribe(cb))."),
    # LINQ / Rx operator aliases. Neither exists: aliases for the same operation
    # were rejected outright, and `where` in particular now has a real counterpart
    # whose required seed is the whole point.
    (re.compile(r"\.(?:where|select)\s*\(\s*lambda\b"), "Rx/LINQ",
     "No where/select aliases. Filtering is .filter(pred, initial=...) — initial is required "
     "and keyword-only, because a filtered Observable has no value until something passes. "
     "Projection is .map(fn)."),
    (re.compile(r"\bIndexedStack\b|\bBottomNavigationBar\b"), "Flutter",
     "No IndexedStack / BottomNavigationBar: switch children with nv.Deck(index=obs, "
     "children=[...]); left-hand nav is nv.NavigationRail."),
]


# The same dead chain as the RULES entry above, but split across two lines:
#
#     debounced = self.raw_count.debounce(0.5)     # local, not stored on self
#     debounced.subscribe(cb)                      # Disposable discarded too
#
# Neither line is damning alone — a local is fine if the Disposable is kept, and
# a bare `.subscribe(` is fine on something that is held — so this needs both
# halves, which a line-at-a-time rule cannot see.
#
# Scoped to __init__ / on_mount, and that scoping is load-bearing rather than
# cautious. A local holds the chain for the rest of the call, so this shape is
# perfectly correct in a function that also *uses* it before returning — which is
# what most test code looks like. It is only a bug where the chain has to outlive
# the call, and setup methods are where that is certain: whatever is being set up
# keeps running afterwards. Retaining either half (`self._sub = x.subscribe(...)`,
# `self.bind(x.subscribe(...))`) is legitimate anywhere and never fires.
_SETUP_DEF = re.compile(r"^([ \t]*)def\s+(?:__init__|on_mount)\s*\(")
_LOCAL_WRAPPER = re.compile(r"^[ \t]+([A-Za-z_]\w*)\s*=\s*[^=].*\.(?:debounce|throttle|filter)\s*\(")
_DISCARDED_SUBSCRIBE = r"^[ \t]*{name}\s*\.\s*subscribe\s*\("

_DEAD_CHAIN_FIX = (
    "Hold what you derive: this local debounce/throttle/filter Observable is collected when the "
    "setup method returns, and the discarded Disposable does not hold it either, so it "
    "never fires. Store one of them: self._sub = source.debounce(0.5).subscribe(cb), or "
    "self.bind(...) in a widget."
)


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip())


def find_dead_chains(text: str) -> list[tuple[int, str]]:
    """``(lineno, source)`` for setup-local wrapper chains whose Disposable is dropped."""
    lines = [strip_comment(raw) for raw in text.splitlines()]
    findings = []
    body_indent: int | None = None

    for index, line in enumerate(lines):
        setup = _SETUP_DEF.match(line)
        if setup:
            body_indent = len(setup.group(1))
            continue
        if body_indent is None or not line.strip():
            continue
        if _indent_of(line) <= body_indent:
            body_indent = None  # dedented out of the setup method
            continue

        candidate = _LOCAL_WRAPPER.match(line)
        if not candidate:
            continue
        subscribe = re.compile(_DISCARDED_SUBSCRIBE.format(name=re.escape(candidate.group(1))))
        for follow_index in range(index + 1, len(lines)):
            follow = lines[follow_index]
            if follow.strip() and _indent_of(follow) <= body_indent:
                break  # left the setup method without ever holding it
            if subscribe.match(follow) and "=" not in follow and "bind(" not in follow:
                findings.append((follow_index + 1, text.splitlines()[follow_index].strip()))
                break
    return findings


# An `on_mount` override on a ComposableWidget that never calls `super()`.
#
# The base implementation is what runs `build()`, so skipping it mounts a widget
# with no children: a blank screen, no exception, nothing in the log. It is the
# quietest failure in the framework, and the shape that causes it -- needing
# `X.of(self)`, which cannot run in `__init__` -- is exactly what the references
# tell an author to write.
#
# Scoped to ComposableWidget subclasses on purpose. `Widget.on_mount` is a no-op,
# so omitting `super()` there costs nothing and flagging it would be noise;
# `BuilderHostMixin.on_mount` is the one with work to do.
_COMPOSABLE_CLASS = re.compile(r"^([ \t]*)class\s+\w+\s*\([^)]*\bComposableWidget\b")
_ON_MOUNT_DEF = re.compile(r"^([ \t]*)def\s+on_mount\s*\(")
_SUPER_ON_MOUNT = re.compile(r"\bsuper\s*\(\s*\)\s*\.\s*on_mount\s*\(")

_MISSING_SUPER_FIX = (
    "Call super().on_mount() in the override. The base implementation is what runs build(), "
    "so without it the widget mounts with no children -- a blank screen. A debug build raises "
    "on it at mount time; under python -O it stays silent. "
    "Place it before your setup, or after it if build() reads what the setup produces."
)


def find_missing_super_on_mount(text: str) -> list[tuple[int, str]]:
    """``(lineno, source)`` for ComposableWidget ``on_mount`` overrides missing ``super()``."""
    raw_lines = text.splitlines()
    lines = [strip_comment(raw) for raw in raw_lines]
    findings = []
    class_indent: int | None = None

    for index, line in enumerate(lines):
        klass = _COMPOSABLE_CLASS.match(line)
        if klass:
            class_indent = len(klass.group(1))
            continue
        if class_indent is None or not line.strip():
            continue
        if _indent_of(line) <= class_indent:
            class_indent = None  # dedented out of the class body
            continue

        method = _ON_MOUNT_DEF.match(line)
        if not method:
            continue
        body_indent = len(method.group(1))
        for follow in lines[index + 1:]:
            if follow.strip() and _indent_of(follow) <= body_indent:
                break  # end of the override, no super() seen
            if _SUPER_ON_MOUNT.search(follow):
                break
        else:
            findings.append((index + 1, raw_lines[index].strip()))
            continue
        if not _SUPER_ON_MOUNT.search(follow):
            findings.append((index + 1, raw_lines[index].strip()))
    return findings


def iter_py_files(targets: list[str]):
    for t in targets:
        p = Path(t)
        if p.is_dir():
            yield from p.rglob("*.py")
        elif p.suffix == ".py":
            yield p


def strip_comment(line: str) -> str:
    """Crudely drop trailing line comments to cut false positives.

    Not string-aware; acceptable because our tokens rarely appear in strings and
    this only reduces noise, never suppresses a real code hit outside comments.
    """
    in_s = None
    for i, ch in enumerate(line):
        if in_s:
            if ch == in_s:
                in_s = None
        elif ch in "\"'":
            in_s = ch
        elif ch == "#":
            return line[:i]
    return line


def main(argv: list[str]) -> int:
    # Scanned lines (and this file's pointers) may contain non-ASCII; force UTF-8
    # so output never dies on a Windows cp932 / other narrow console.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")

    targets = argv[1:]
    if not targets:
        print(__doc__)
        return 0

    findings = 0
    for path in iter_py_files(targets):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, raw in enumerate(text.splitlines(), 1):
            line = strip_comment(raw)
            if not line.strip():
                continue
            for pattern, framework, fix in RULES:
                if pattern.search(line):
                    findings += 1
                    print(f"{path}:{lineno}: [{framework}] {raw.strip()}")
                    print(f"    -> {fix}")

        for lineno, source in find_dead_chains(text):
            findings += 1
            print(f"{path}:{lineno}: [Rx habit] {source}")
            print(f"    -> {_DEAD_CHAIN_FIX}")

        for lineno, source in find_missing_super_on_mount(text):
            findings += 1
            print(f"{path}:{lineno}: [lifecycle] {source}")
            print(f"    -> {_MISSING_SUPER_FIX}")

    if findings:
        print(f"\n{findings} foreign-idiom warning(s). See "
              "skills/nuiitivet-app/references/translation.md")
        return 1
    print("No foreign-framework idioms detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
