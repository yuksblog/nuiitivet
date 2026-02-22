# Navigation samples

These samples are aligned with `docs/guide/navigation*.md` as far as the current framework API allows.

## Current limitations

- `MaterialNavigator(NestedHome())` is not supported yet. `sub.py` uses `MaterialNavigator(routes=[PageRoute(...)])`.
- `NavigationProxy` type is not available yet. `intent.py` uses `Navigator` directly in the ViewModel example.
