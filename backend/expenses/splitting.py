"""
Expense splitting — turns an expense into per-person shares.

Every function returns a list of (user_id, amount_paisa, percentage) tuples whose
amounts add up EXACTLY to the expense total. Working in integer paisa means
Rs. 100 split 3 ways becomes 33.34 + 33.33 + 33.33 instead of 33.33 x 3 = 99.99.
"""

from decimal import ROUND_HALF_UP, Decimal


class SplitError(ValueError):
    """Raised when split input is invalid. The message is shown to the user."""


def _distribute_remainder(shares, remainder, order):
    """Give leftover paisa one at a time, in `order`, so totals match exactly."""
    i = 0
    while remainder > 0:
        shares[order[i % len(order)]] += 1
        remainder -= 1
        i += 1
    return shares


def split_equal(total_paisa, user_ids):
    if not user_ids:
        raise SplitError("Select at least one participant.")
    if len(set(user_ids)) != len(user_ids):
        raise SplitError("A participant was selected twice.")
    count = len(user_ids)
    base, remainder = divmod(total_paisa, count)
    shares = {uid: base for uid in user_ids}
    _distribute_remainder(shares, remainder, list(user_ids))
    return [(uid, shares[uid], None) for uid in user_ids]


def split_custom(total_paisa, amounts):
    """amounts: list of (user_id, amount_paisa)."""
    if not amounts:
        raise SplitError("Enter an amount for at least one participant.")
    ids = [uid for uid, _ in amounts]
    if len(set(ids)) != len(ids):
        raise SplitError("A participant was entered twice.")
    if any(a < 0 for _, a in amounts):
        raise SplitError("Amounts cannot be negative.")
    entered = sum(a for _, a in amounts)
    if entered != total_paisa:
        diff = (Decimal(total_paisa - entered) / 100).quantize(Decimal("0.01"))
        hint = f"Rs. {abs(diff)} {'left to assign' if diff > 0 else 'too much'}"
        raise SplitError(
            f"Custom amounts must add up to the expense total ({hint})."
        )
    result = [(uid, a, None) for uid, a in amounts if a > 0]
    if not result:
        raise SplitError("At least one participant must have an amount above zero.")
    return result


def split_percentage(total_paisa, percentages):
    """percentages: list of (user_id, Decimal percentage)."""
    if not percentages:
        raise SplitError("Enter a percentage for at least one participant.")
    ids = [uid for uid, _ in percentages]
    if len(set(ids)) != len(ids):
        raise SplitError("A participant was entered twice.")
    if any(p < 0 for _, p in percentages):
        raise SplitError("Percentages cannot be negative.")
    total_pct = sum((p for _, p in percentages), Decimal("0"))
    if total_pct != Decimal("100"):
        raise SplitError(f"Percentages must add up to 100% (currently {total_pct.normalize():f}%).")

    shares = {}
    for uid, pct in percentages:
        exact = Decimal(total_paisa) * pct / Decimal(100)
        shares[uid] = int(exact.to_integral_value(rounding=ROUND_HALF_UP))

    # Fix rounding so the total is exact: adjust the largest shares first
    diff = total_paisa - sum(shares.values())
    order = sorted(shares, key=lambda u: (-shares[u], ids.index(u)))
    step = 1 if diff > 0 else -1
    i = 0
    while diff != 0:
        uid = order[i % len(order)]
        if shares[uid] + step >= 0:
            shares[uid] += step
            diff -= step
        i += 1

    pct_map = dict(percentages)
    return [(uid, shares[uid], pct_map[uid]) for uid in ids if pct_map[uid] > 0]
