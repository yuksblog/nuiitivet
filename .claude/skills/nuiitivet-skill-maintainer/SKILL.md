---
name: nuiitivet-skill-maintainer
description: Keep the text a coding agent reads -- the published skills in skills/ and the dev bridge MCP server text -- accurate against the framework.
---

# Nuiitivet Skill Maintainer

Keep the text a coding agent reads in sync with the framework: the published
skills under `skills/` (`nuiitivet-app`, `nuiitivet-debug`,
`nuiitivet-see-comments`) and the dev bridge MCP server text in
`src/nuiitivet/dev/mcp_server.py` (the server instructions and each tool
description). A maintainer workflow, not a user-facing skill.

Every published skill is self-contained, link-free, and verified against the
real source; only `nuiitivet-app` has a linter. The boundaries: authoring
idioms in `nuiitivet-app`; running, inspecting and driving the live app in
`nuiitivet-debug`; acting on the user's in-app comments in
`nuiitivet-see-comments`.

## When to Use

- A public `nv.*` symbol is added, renamed or removed (widget, modifier,
  Observable operator, Navigator/Overlay method, style).
- You hit a mistake or a foreign-framework anti-pattern the skill does not
  warn about yet.
- An idiom changes (a construction pattern, a recommended approach).
- An MCP tool is added, renamed or changes what it returns, or the set of
  published skills changes; the server instructions name the skills.

Note the insight at once (an issue), then run this workflow.

## The One Rule

**Prose and linter move in lockstep.** Every anti-pattern lives in two places,
updated together:

1. `skills/nuiitivet-app/references/translation.md` (and the matching topical
   reference): the "tempted to write X → write Y" row.
2. `skills/nuiitivet-app/scripts/check_idioms.py`: a `RULES` entry, a
   high-confidence regex plus the pointer to the nuiitivet fix.

Updating one leaves the skill lying to itself: the prose warns and the linter
is silent, or the reverse.

## Workflow

1. **Classify the change**: API change, new anti-pattern, idiom change, MCP
   change. If it does not affect the published text, stop. A new or changed
   API also names the foreign habit it replaces (`maxLines`, `TextArea`):
   translation row and linter rule first, reference text second.
2. **Locate every touchpoint**: grep the whole skill for the symbol or claim.
   ```
   grep -rn "<old-name-or-claim>" skills/nuiitivet-app/
   ```
3. **Verify against the real source; never trust memory or the old text.**
   Confirm each name and signature from `src/nuiitivet/` (Verification Gate).
   The original draft shipped `radius`, `IndexedStack`, `push_replacement`;
   none exist.
4. **Apply the edit** in the right file. Each sentence passes **Guardrails**
   before it is written: what a parameter means is the docstring's, which the
   agent reads for every parameter the skill does not list.
   - API renamed or removed → fix every snippet and table row; update the
     widget catalog in `SKILL.md`.
   - New anti-pattern → the prose row **and** a `check_idioms.py` rule (The
     One Rule).
   - New widget → a catalog row in `SKILL.md` with a *verified* construction
     snippet.
   - New or changed idiom → the topical reference and every example.
   - Missing judgement → fold it into the references. No site link: a link
     next to a task gets followed and short-circuits maintenance.
5. **Run the Verification Gate.** Fix until all pass.
6. **Commit** as `docs(skills):` or `feat(skills):`; PR via
   `/pull-request-manager` when it warrants review.

## Wording

The reader is an agent. It does not fill a gap from context; it invents
something, or follows whichever fragment it retrieved. This holds for every
published skill and for the MCP server text.

- **A new feature goes into the skill's outline, not into a section appended
  for it.** An appended section ends up restating the skill. A heading is
  added only for a task the agent would search for; an option of an existing
  task goes into that task's snippet or one sentence. Sibling headings divide
  their parent on one axis, with no gap and no overlap.
- **Every prohibition names its replacement, adjacent.** "Do not `setState`"
  alone buys a *different* wrong answer; the `nv` idiom goes in the same
  sentence or the next line.
- **Short sentences, dense from the first line to the last.** Each sentence
  carries one fact the reader does not have. A fact is stated once; it is
  repeated only where the two places are far apart.
- **No hedging.** "Generally", "prefer", "you may want to" hand the decision
  back. State the rule, or the condition that selects between two rules.
- **Real symbols, not descriptions.** `nv.ComposableWidget`, never "the
  composable base class": greppable, checkable with `hasattr`.
- **No unresolved reference.** "As above", "the previous section" do not
  survive being read as a fragment. Name the file or the heading.
- **Wrong code is labelled, and sits next to the right code.** An unlabelled
  bad snippet gets copied.
- **One rule, one canonical statement.** The same rule reworded in two places
  contradicts itself the moment one copy is edited. The prose ↔
  `check_idioms.py` pair is the deliberate exception (The One Rule).
- **Handover between skills runs one way**: from the skill the user invokes to
  the skill that carries the loop, never back.

## MCP Server Text

`src/nuiitivet/dev/mcp_server.py` carries two texts the agent reads without
asking: the server instructions and one description per tool.

- **The server instructions** carry what the server drives, which question
  goes to which tool (one clause each), and the skill names. Not procedure,
  not judgement, not any one tool's details.
- **A tool description** carries what the tool returns and when to call it.
  Not a field-by-field walkthrough, not a procedure, not what the returned
  JSON already shows.
- **The text assumes the skills are installed.** A tool description does not
  stand in for a missing skill: the procedure goes into the skill, and the
  instructions name the skill.
- **A host may cut what it is sent.** Claude Code cuts the server instructions
  and each tool description at 2048 characters; a text that runs long loses
  its end without an error. `tests/dev/test_mcp_server.py` holds every text
  under the limit.

## Verification Gate — all must pass

Run each item; never assert it.

- [ ] Every `nv.*` claim exists. For each symbol touched:
  ```
  python -c "import nuiitivet.material as nv; print(hasattr(nv, '<Name>'))"
  ```
  For a signature, read `src/nuiitivet/...` or
  `inspect.signature(getattr(nv, '<Name>').__init__)`.
- [ ] Snippets construct and run: each changed snippet pasted into a throwaway
  script and executed. A snippet that raises on construction is a bug in the
  skill.
- [ ] Linter clean on real code, sharp on bad code:
  ```
  python skills/nuiitivet-app/scripts/check_idioms.py samples/   # expect: no findings
  ```
  then a planted file with the new anti-pattern is flagged with the right
  pointer. A rule that fires on `samples/` is a false positive: tighten the
  regex to a signature unique to the foreign framework.
- [ ] Prose and linter in lockstep: every habit a translation row names, the
  linter flags, and the reverse (The One Rule).
- [ ] No external URL: `grep -rn "https://" skills/nuiitivet-app/ skills/nuiitivet-debug/`
  returns nothing.
- [ ] MCP text within the host limit: `uv run pytest tests/dev/test_mcp_server.py`
  after any change to the server instructions or a tool description.
- [ ] Every changed sentence is procedure, judgement, or the idiom beside the
  habit it replaces (Guardrails); a parameter explained is a docstring copy.
- [ ] Every prohibition has its replacement adjacent; no hedge in a rule
  (Wording).
- [ ] Short sentences, one fact each, dense throughout; a fact repeated only
  where two places are far apart — checked on each changed paragraph.
- [ ] Sibling headings divide their parent on one axis, no gap, no overlap —
  checked on the whole file, not only the section touched.

## Adding a check_idioms.py rule

A rule is `(compiled_regex, framework, fix_pointer)`. Match a token or shape
with no legitimate use in nuiitivet (`\bStatefulWidget\b`, `showDialog\s*\(`),
never a common word. The `fix` string names the real nuiitivet idiom, verified
this session. Then re-run the gate: clean on `samples/`, fires on the planted
example.

## Guardrails

- The skill teaches idioms and the high-frequency intent → widget mapping, not
  every parameter; it is not a second framework manual.
- A skill carries the agent's procedure and judgement, and a rule only for a
  mistake actually made. Not what the human does, not what a tool returns
  (the tool description says that), not a precaution nobody has hit.
- A breaking, correct update over back-compat cruft, as in the framework.
