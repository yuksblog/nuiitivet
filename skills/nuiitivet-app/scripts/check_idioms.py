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
     "Navigator.root() / Overlay.root() are gone (#518): a process-global root cannot "
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
    (re.compile(r"\bpushReplacement\b|\bpushNamed\b|\bpopUntil\b"), "Flutter",
     "No push_replacement / pop_until in Nuiitivet: push a widget or Intent with "
     "Navigator.of(self).push(...); go back with Navigator.of(self).pop()."),
    (re.compile(r"\brunApp\s*\(|\bMaterialApp\s*\("), "Flutter",
     "nv.App(content=build_root).run() — pass a factory for hot reload."),
    (re.compile(r"\bBuildContext\b"), "Flutter",
     "No BuildContext type; context is passed where needed without annotation."),
    (re.compile(r"@Composable\b"), "Jetpack Compose",
     "Define a ComposableWidget subclass with build(self)."),
    (re.compile(r"\bcomputed\s*\(|\bobservable\s*\(\s*\)|\bmakeAutoObservable\b"), "MobX/Vue",
     "Derived state: a.combine(b).compute(lambda a, b: ...)."),
    (re.compile(r"\bIndexedStack\b|\bBottomNavigationBar\b"), "Flutter",
     "No IndexedStack / BottomNavigationBar: switch children with nv.Deck(index=obs, "
     "children=[...]); left-hand nav is nv.NavigationRail."),
]


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

    if findings:
        print(f"\n{findings} foreign-idiom warning(s). See "
              "skills/nuiitivet-app/references/translation.md")
        return 1
    print("No foreign-framework idioms detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
