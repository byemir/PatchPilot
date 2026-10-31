"""Shared rules of the inventory package (written for this repository)."""
LOW = 5


def is_low(qty):
    return qty < LOW


def target_for(name):
    return 20 if name.startswith("bulk") else 10
