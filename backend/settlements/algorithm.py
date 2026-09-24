"""
Smart settlement algorithm (pure Python, no database).

Input : net balance per person in paisa.
        positive  -> should RECEIVE money (creditor)
        negative  -> should GIVE money   (debtor)
        The balances of a group always sum to zero.

Output: a list of (debtor_id, creditor_id, amount_paisa) payments that brings
        everyone to zero.

Steps
1. Drop people who are already settled (balance 0).
2. Exact matches first: if a debtor owes exactly what a creditor is owed,
   pair them - one payment clears two people at once.
3. Greedy matching: repeatedly take the person who owes the most and the
   person who is owed the most, and transfer min(owes, owed). At least one of
   the two is cleared by every payment.

Because every payment clears at least one person, a group with N people who
are not settled needs at most N - 1 payments - usually far fewer than paying
back every individual expense separately. (Finding the absolute minimum is an
NP-hard problem; this greedy approach is the standard, predictable choice.)

Ties are broken by the `order` value (e.g. the name) so the plan is stable and
does not change randomly between page reloads.
"""


def minimize_transactions(balances, order=None):
    """
    balances: dict {person_id: paisa}
    order:    optional dict {person_id: sortable key} for deterministic ties
    """
    if sum(balances.values()) != 0:
        raise ValueError("Balances must add up to zero.")

    order = order or {}

    def key(pid):
        return (order.get(pid, ""), str(pid))

    debtors = {pid: -amt for pid, amt in balances.items() if amt < 0}
    creditors = {pid: amt for pid, amt in balances.items() if amt > 0}
    payments = []

    # Step 2 - exact matches
    for debtor in sorted(debtors, key=lambda p: (-debtors[p], key(p))):
        for creditor in sorted(creditors, key=key):
            if creditors[creditor] == debtors[debtor]:
                payments.append((debtor, creditor, debtors[debtor]))
                del creditors[creditor]
                debtors[debtor] = 0
                break
    debtors = {p: a for p, a in debtors.items() if a > 0}

    # Step 3 - greedy: biggest debtor pays biggest creditor
    while debtors and creditors:
        debtor = min(debtors, key=lambda p: (-debtors[p], key(p)))
        creditor = min(creditors, key=lambda p: (-creditors[p], key(p)))
        amount = min(debtors[debtor], creditors[creditor])
        payments.append((debtor, creditor, amount))

        debtors[debtor] -= amount
        creditors[creditor] -= amount
        if debtors[debtor] == 0:
            del debtors[debtor]
        if creditors[creditor] == 0:
            del creditors[creditor]

    return payments


def count_direct_debts(pairwise):
    """How many payments would be needed without optimisation (one per owing pair)."""
    return sum(1 for amount in pairwise.values() if amount > 0)
