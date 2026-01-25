"""Auto-fix helper: generate patches to convert construction-time color
assignments into paint-time theme-resolved ColorRole usages.

This script is conservative and DOES NOT modify source files by itself.
Instead it generates unified diffs under `patches/` which you can review
and apply manually.

Usage:
    python3 scripts/dev/repo/auto_fix_color_resolution.py

Output:
  - patches/<relpath>.patch : unified diff applying suggested replacements

Notes:
  - The script only targets assignments inside `__init__` to attributes on
    `self` such as `self.bgcolor`, `self.border_color`, `self.shadow_color`,
    `self.color`.
  - Replacement strategy is conservative: replace literal hex strings and
    simple material tokens (e.g. material.PRIMARY) with a semantic
    `ColorRole` expression where appropriate.
  - For shadow_color if an alpha is present or default used, the script
    prefers a tuple form like `(ColorRole.SHADOW, 0.24)` so alpha is
    preserved.
"""

from __future__ import annotations

import ast
import difflib
import os
import re
from typing import Dict, List, Optional, Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PKG = os.path.join(ROOT, "nuiitivet")
PATCH_DIR = os.path.join(ROOT, "patches")

# target attributes and suggested ColorRole defaults
ATTR_TO_ROLE: Dict[str, str] = {
    "bgcolor": "ColorRole.BACKGROUND",
    "border_color": "ColorRole.OUTLINE",
    "shadow_color": "ColorRole.SHADOW",
    "color": "ColorRole.ON_SURFACE",
    "fill_color": "ColorRole.PRIMARY",
    "stroke_color": "ColorRole.OUTLINE",
}

TARGET_ATTRS = set(ATTR_TO_ROLE.keys())


class InitAssignFinder(ast.NodeVisitor):
    def __init__(self):
        self.repls: List[Tuple[int, str, str]] = []  # lineno, attr, replacement_code
        self._in_init = False

    def visit_FunctionDef(self, node: ast.FunctionDef):
        prev = self._in_init
        if node.name == "__init__":
            self._in_init = True
            for n in node.body:
                self.visit(n)
        self._in_init = prev

    def visit_Assign(self, node: ast.Assign):
        if not self._in_init:
            return
        for t in node.targets:
            if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
                attr = t.attr
                if attr in TARGET_ATTRS:
                    repl = self._suggest_replacement(node.value, attr)
                    if repl:
                        self.repls.append((getattr(node, "lineno", 0), attr, repl))

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if not self._in_init:
            return
        t = node.target
        if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
            attr = t.attr
            if attr in TARGET_ATTRS and node.value is not None:
                repl = self._suggest_replacement(node.value, attr)
                if repl:
                    self.repls.append((getattr(node, "lineno", 0), attr, repl))

    def _suggest_replacement(self, node: ast.AST, attr: str) -> Optional[str]:
        """Return replacement Python source string or None if no safe suggestion."""
        # literal hex string
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            v = node.value.strip()
            if re.match(r"^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$", v):
                role = ATTR_TO_ROLE.get(attr)
                if role:
                    # For bgcolor, border_color etc, replace with ColorRole.X
                    return role
        # material token like material.PRIMARY
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "material":
            role = ATTR_TO_ROLE.get(attr)
            if role:
                return role
        # tuple (something, alpha) -> keep alpha when mapping to (ColorRole.X, alpha)
        if isinstance(node, ast.Tuple) and len(node.elts) == 2:
            fst, snd = node.elts
            # fst is string or material token
            if (
                isinstance(fst, ast.Constant)
                and isinstance(fst.value, str)
                and re.match(r"^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$", fst.value)
            ):
                role = ATTR_TO_ROLE.get(attr)
                if role:
                    try:
                        # produce literal alpha value if numeric literal
                        if isinstance(snd, ast.Constant) and isinstance(snd.value, (int, float)):
                            return f"({role}, {float(snd.value)})"
                    except Exception:
                        return f"({role}, {1.0})"
            if isinstance(fst, ast.Attribute) and isinstance(fst.value, ast.Name) and fst.value.id == "material":
                role = ATTR_TO_ROLE.get(attr)
                if role:
                    if isinstance(snd, ast.Constant) and isinstance(snd.value, (int, float)):
                        return f"({role}, {float(snd.value)})"
        # name referring to ColorRole already
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "ColorRole":
            return None  # already fine
        # fallback: do not suggest
        return None


def suggest_param_default_changes(src: str) -> List[Tuple[int, str, str, str]]:
    """Find __init__ parameter defaults that can be changed to ColorRole.

    Returns list of (lineno, param_name, old_text, new_text) where lineno is
    the line number of the def signature (approx), and old_text/new_text are
    the replacement snippets for the parameter default (e.g. 'bgcolor=None' ->
    'bgcolor=ColorRole.BACKGROUND').
    """
    out: List[Tuple[int, str, str, str]] = []
    try:
        tree = ast.parse(src)
    except Exception:
        return out

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "__init__":
            continue
        # get arg names and defaults (ast packs defaults aligned to last N args)
        args = [a.arg for a in node.args.args]
        defaults = node.args.defaults
        num_defaults = len(defaults)
        arg_defaults: Dict[str, ast.AST] = {}
        if num_defaults:
            for i, d in enumerate(defaults):
                arg_name = args[len(args) - num_defaults + i]
                arg_defaults[arg_name] = d

        # scan body for assigns self.attr = param
        for stmt in node.body:
            if not isinstance(stmt, ast.Assign):
                continue
            for t in stmt.targets:
                if not (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self"):
                    continue
                attr = t.attr
                if attr not in TARGET_ATTRS:
                    continue
                # RHS should be a parameter name
                if not isinstance(stmt.value, ast.Name):
                    continue
                param = stmt.value.id
                if param not in arg_defaults:
                    continue
                default_node = arg_defaults[param]
                # suggest only if default is None
                role = ATTR_TO_ROLE.get(attr)
                if role is None:
                    continue
                if isinstance(default_node, ast.Constant) and default_node.value is None:
                    old = f"{param}=None"
                    if attr == "shadow_color":
                        new = f"{param}=({role}, 0.24)"
                    else:
                        new = f"{param}={role}"
                    out.append((node.lineno, param, old, new))
                # or if default is a simple material token like material.X
                elif (
                    isinstance(default_node, ast.Attribute)
                    and isinstance(default_node.value, ast.Name)
                    and default_node.value.id == "material"
                ):
                    old = f"{param}={ast.unparse(default_node) if hasattr(ast, 'unparse') else 'material.X'}"
                    if attr == "shadow_color":
                        new = f"{param}=({role}, 0.24)"
                    else:
                        new = f"{param}={role}"
                    out.append((node.lineno, param, old, new))
    return out


def generate_patch(orig_src: str, new_src: str, relpath: str) -> Optional[str]:
    if orig_src == new_src:
        return None
    a = orig_src.splitlines(keepends=True)
    b = new_src.splitlines(keepends=True)
    diff = difflib.unified_diff(a, b, fromfile=relpath, tofile=relpath + " (patched)")
    return "".join(diff)


def process_file(path: str) -> Optional[Tuple[Optional[str], str]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
    except Exception:
        return None
    try:
        tree = ast.parse(src)
    except Exception:
        return None
    v = InitAssignFinder()
    v.visit(tree)
    param_changes = suggest_param_default_changes(src)
    if not v.repls and not param_changes:
        return None
    # Build new source lines and apply replacements at lineno positions (conservative)
    lines = src.splitlines()
    # create a mapping lineno -> (attr, repl)
    repl_map: Dict[int, Tuple[str, str]] = {ln: (attr, repl) for (ln, attr, repl) in v.repls}

    new_lines = list(lines)
    # For safety, we will replace the RHS expression on the same line using a regex
    for ln, (attr, repl) in sorted(repl_map.items(), reverse=True):
        idx = ln - 1
        if idx < 0 or idx >= len(new_lines):
            continue
        line = new_lines[idx]
        # naive pattern: self.<attr> = <anything>
        m = re.match(r"(\s*self\." + re.escape(attr) + r"\s*=\s*).+", line)
        if m:
            prefix = m.group(1)
            # Use replacement code; ensure imports handled by reviewer
            new_lines[idx] = prefix + repl
        else:
            # try annotated assign style: self.attr: Type = <expr>
            m2 = re.match(r"(\s*self\." + re.escape(attr) + r"\s*:\s*[^=]+=\s*).+", line)
            if m2:
                prefix = m2.group(1)
                new_lines[idx] = prefix + repl
            else:
                # can't safely replace this line; skip
                continue

    new_src = "\n".join(new_lines) + ("\n" if src.endswith("\n") else "")
    # Apply param default changes: replace on the def signature line if possible
    if param_changes:
        new_lines2 = new_src.splitlines()
        for lineno, param, old, new in param_changes:
            idx = lineno - 1
            # Build a regex to match the parameter default in the signature line
            param_pattern = re.compile(rf"\b{re.escape(param)}\b\s*(?:\:[^=]+)?\s*=\s*[^,\)]+")
            if 0 <= idx < len(new_lines2):
                line = new_lines2[idx]
                if param_pattern.search(line):
                    new_lines2[idx] = param_pattern.sub(f"{new}", line, count=1)
                else:
                    # try to find the def __init__ line in the first 40 lines
                    replaced = False
                    for i, l in enumerate(new_lines2[:40]):
                        if l.strip().startswith("def __init__") and param_pattern.search(l):
                            new_lines2[i] = param_pattern.sub(f"{new}", l, count=1)
                            replaced = True
                            break
                    if not replaced:
                        # fallback: try a looser global replacement for the first match
                        joined = "\n".join(new_lines2)
                        m = param_pattern.search(joined)
                        if m:
                            joined = param_pattern.sub(f"{new}", joined, count=1)
                            new_lines2 = joined.splitlines()
        new_src = "\n".join(new_lines2) + ("\n" if src.endswith("\n") else "")
        # Ensure ColorRole is imported if we introduced any ColorRole usage
    if "ColorRole." in new_src and "from .color_role import ColorRole" not in new_src:
        # insert import after other local imports (after first block of from/imports)
        nl = new_src.splitlines()
        insert_at = 0
        for i, l in enumerate(nl[:40]):
            if l.strip().startswith("from .") or l.strip().startswith("import "):
                insert_at = i + 1
        nl.insert(insert_at, "from .color_role import ColorRole")
        new_src = "\n".join(nl) + ("\n" if src.endswith("\n") else "")
    patch = generate_patch(src, new_src, os.path.relpath(path, ROOT))
    return (patch, new_src)


def main():
    if not os.path.isdir(PATCH_DIR):
        os.makedirs(PATCH_DIR, exist_ok=True)

    patches_created = 0
    for root, dirs, files in os.walk(PKG):
        for fn in files:
            if not fn.endswith(".py"):
                continue
            p = os.path.join(root, fn)
            res = process_file(p)
            if res is None:
                continue
            patch, new_src = res
            if not patch:
                continue
            rel = os.path.relpath(p, ROOT)
            outpath = os.path.join(PATCH_DIR, rel.replace(os.sep, "__") + ".patch")
            with open(outpath, "w", encoding="utf-8") as f:
                f.write(patch)
            patches_created += 1
            print(f"Wrote patch: {outpath}")

    print(f"Patches generated: {patches_created}")


if __name__ == "__main__":
    main()
