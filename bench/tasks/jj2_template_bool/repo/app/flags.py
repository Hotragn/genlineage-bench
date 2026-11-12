# Feature flags.
ENABLED = frozenset({
    "fast_checkout",
    "beta_search",
    "gift_cards",
})


def is_enabled(name):
    return name in ENABLED
