---
name: material-spec-collector
description: Collect Material Design 3 component specs and design tokens from m3.material.io into docs/md3/ in the buttons.md table format.
---

# Material Spec Collector

Collect a Material Design 3 component's specs and design tokens from
`m3.material.io` into `docs/md3/`.

## Output Contract

- Read `docs/md3/buttons.md` first; the new page mirrors its structure.
- Write to `docs/md3/<component_name>.md` (snake_case).
- Sections: title, source URL, collected date, summary bullets,
  `## Tokens & Specs`, `### Token Sets Discovered`, one table per token set
  with the columns `Token Set | Group | Label | Token | Source token | Value | Notes`.

## Workflow

### 1. Inspect the live spec page

Open the component's `specs` page and note which token sets the current
viewer shows.

- `Tokens & specs` and `Baseline tokens & specs` are separate sets.
- Deprecated and baseline sets stay out unless the user asks.
- With several viewers, take the first (current) one.

### 2. Find the token JSON in network resources

The JSON is the source of truth; the DOM only confirms which sets are exposed.
On `m3.material.io` it is `_dsm/data/dsdb-m3/.../TOKEN_TABLE...json`.

### 3. Context selection

A token with several contextual entries takes the first available of:

1. Light + Default + Expressive
2. Light + Default
3. the first entry

Tag IDs:

- Light: `...tags/0b5c40268cdb2499`
- Default: `...tags/215f4693b82ba1df`
- Expressive: `...tags/33f628e37aed5bee`

### 4. Source token lineage

`Source token` comes from `referenceTree`: the nearest `md.sys.*` token, or
the nearest referenced token when there is none.

### 5. Value formatting

- Colors: `#RRGGBB`
- Opacity: decimal string (`0.08`)
- Length, elevation: `dp`
- Shape: corner size, `20dp`
- A shadow that is black with `alpha: 1`: `#000000`

### 6. Groups

From the token name suffix: `Enabled`, `Disabled`, `Hovered`, `Focused`,
`Pressed`, `Layout`, `Shape`, `Motion`.

## Validation

- Spot-check representative values against the live viewer.
- No table is empty.
- One container color per color variant, one size token per size set.
