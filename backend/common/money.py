"""
Money helpers.

All money is stored as Decimal with 2 decimal places (NPR and paisa).
Calculations that must add up exactly (splits, balances, settlement plans)
are done in integer paisa (1 rupee = 100 paisa) to avoid rounding drift.
"""

from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")
MAX_AMOUNT = Decimal("10000000.00")  # Rs. 1 crore upper bound per expense/settlement


def to_decimal(value):
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def to_paisa(value):
    return int((to_decimal(value) * 100).to_integral_value(rounding=ROUND_HALF_UP))


def from_paisa(paisa):
    return (Decimal(paisa) / 100).quantize(TWO_PLACES)


def format_npr(value):
    """Rs. 1,25,000 style (South Asian grouping) - used in notifications/activity."""
    amount = to_decimal(value)
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    rupees = int(amount)
    paisa = int((amount - rupees) * 100)
    digits = str(rupees)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups) + "," + tail
    text = f"Rs. {digits}"
    if paisa:
        text += f".{paisa:02d}"
    return sign + text
