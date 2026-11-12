# Rendered from templates/flags.py.j2 by tools/render.py. DO NOT EDIT.
ENABLED = frozenset({
    "fast_checkout",
    "beta_search",
    "gift_cards",
})


def is_enabled(name):
    return name in ENABLED
