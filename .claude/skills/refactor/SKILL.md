---
name: refactor
description: Refactor code without changing behaviour, and the rules for comments and docstrings in src/.
---

# Refactor

Change how the code does it, not what it does.

## Golden Rules

1. **Behaviour is preserved.** What the code does stays; how it does it changes.
2. **Small steps.** One tiny change, then the tests.
3. **Version control.** Commit before, and at every green state.
4. **Tests first.** Without tests it is editing, not refactoring.
5. **One thing at a time.** No feature change in a refactoring commit.

## When Not to Refactor

- Code that works and will not change again
- Critical code without tests: add the tests first
- Under a tight deadline
- "Just because": a refactoring has a purpose

## Common Code Smells & Fixes

| Smell | Fix |
| --- | --- |
| Long Method | Extract into focused functions |
| Duplicated Code | Extract common logic |
| Large Class | Split by single responsibility |
| Long Parameter List | Group into parameter object |
| Feature Envy | Move logic to the object that owns the data |
| Magic Numbers/Strings | Replace with named constants |
| Nested Conditionals | Use guard clauses / early returns |
| Dead Code | Delete it (git history has it) |

## Comments

A comment carries what the code cannot say: a constraint, a trade-off, why
the obvious approach was rejected. A comment that restates the code is
deleted.

- One line at the use site, a couple at most; one fact per sentence
- *Why*, never *what*
- The rationale once, at the definition site, not at every caller
- No link to an issue, a PR or a doc; the comment stands on its own
- A stale comment is worse than none: update or delete it with the code

## Docstrings

A docstring serves the API user: what the caller can observe, behaviour,
timing, constraints, and nothing more. Mechanism and rationale live in
`docs/design/`. The `nuiitivet-app` skill sends the agent to the callable's
docstring for every parameter it does not list, so the docstring is the
agent's instruction.

- A summary line plus a few lines. A mechanism walkthrough (queues, flush
  order, frame phases) belongs in the design doc; one sentence stays here, and
  no pointer
- Current behaviour only. "Instead of X", "as before", "now also" refer to a
  past state the reader cannot see
- A sentence stays only if deleting it loses a fact the caller can observe;
  short sentences, one fact each, dense from the first line to the last
- Extend by rewriting, not appending: draft fresh from the signature and the
  code, then merge in the facts only the old text had. Appended text matches
  the old text, not the code
- A callable documents its own arguments: `__init__` and every public method
  carry their own `Args:`. The class docstring holds no parameter list and
  names the other constructors ("From a data collection: `builder`"). A
  dataclass lists its fields under `Attributes:`. Enforced by
  `tests/test_docstrings_document_their_own_callable.py`

## Safe Refactoring Process

```
1. PREPARE  — ensure tests exist, commit current state
2. IDENTIFY — find the smell, understand what the code does, plan the change
3. REFACTOR — one small change, run tests, commit if passing, repeat
4. VERIFY   — all tests pass, manual testing if needed
5. CLEAN UP — update docs, final commit
```

## Checklist

### Code Quality

- [ ] Functions < 50 lines, do one thing
- [ ] No duplicated code
- [ ] Descriptive names
- [ ] No magic numbers/strings
- [ ] Dead code removed
- [ ] Comments explain intent, not behaviour
- [ ] Docstrings: every sentence carries an observable fact, current behaviour only, no mechanism dumps
- [ ] Comments and docstrings: short sentences, one fact each, dense throughout
- [ ] Docstrings: `Args:` on the callable, no parameter list on the class

### Structure

- [ ] Related code is together
- [ ] Clear module boundaries
- [ ] Dependencies flow in one direction

### Type Safety

- [ ] Types defined for all public APIs
- [ ] Nullable types explicitly marked

### Testing

- [ ] Refactored code is tested
- [ ] All tests pass
