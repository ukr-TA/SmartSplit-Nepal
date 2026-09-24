"""
Balance engine.

For every member of a group:

    net = (total they paid for expenses)
        - (total of their shares of expenses)
        + (successful settlements they paid)
        - (successful settlements they received)

net > 0  -> the group owes them  -> they should RECEIVE
net < 0  -> they owe the group   -> they should GIVE

The nets always add up to zero, which is what lets the smart settlement
algorithm pair givers with receivers.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from django.db.models import Sum

from common.money import from_paisa, to_paisa
from expenses.models import Expense, ExpenseSplit

from .algorithm import count_direct_debts, minimize_transactions
from .models import Settlement


@dataclass
class GroupBalances:
    group: object
    members: list  # User objects (current members)
    paid: dict = field(default_factory=dict)  # user_id -> paisa
    share: dict = field(default_factory=dict)  # user_id -> paisa
    settled_out: dict = field(default_factory=dict)  # user_id -> paisa paid in settlements
    settled_in: dict = field(default_factory=dict)  # user_id -> paisa received
    net: dict = field(default_factory=dict)  # user_id -> paisa
    pairwise: dict = field(default_factory=dict)  # (debtor_id, creditor_id) -> paisa
    plan: list = field(default_factory=list)  # [(from_id, to_id, paisa)]
    users: dict = field(default_factory=dict)  # user_id -> User
    total_spent: int = 0

    # ---- convenience helpers ---------------------------------------------
    def net_of(self, user_id):
        return self.net.get(user_id, 0)

    def plan_for(self, user_id):
        give = [(to, amt) for frm, to, amt in self.plan if frm == user_id]
        receive = [(frm, amt) for frm, to, amt in self.plan if to == user_id]
        return give, receive


def calculate_group_balances(group):
    from groups.models import GroupMember

    memberships = GroupMember.objects.filter(group=group).select_related("user")
    members = [m.user for m in memberships]
    users = {u.pk: u for u in members}

    paid = defaultdict(int)
    share = defaultdict(int)
    settled_out = defaultdict(int)
    settled_in = defaultdict(int)
    debts = defaultdict(int)

    # Expenses: who paid
    for row in Expense.objects.filter(group=group).values("paid_by").annotate(total=Sum("amount")):
        paid[row["paid_by"]] += to_paisa(row["total"])

    # Splits: who owes what, and to whom (for direct pairwise debts)
    splits = ExpenseSplit.objects.filter(expense__group=group).values(
        "user_id", "amount", "expense__paid_by_id"
    )
    for s in splits:
        amt = to_paisa(s["amount"])
        share[s["user_id"]] += amt
        if s["user_id"] != s["expense__paid_by_id"]:
            debts[(s["user_id"], s["expense__paid_by_id"])] += amt

    # Successful settlements
    settlements = Settlement.objects.filter(group=group, status=Settlement.Status.SUCCESSFUL).values(
        "payer_id", "recipient_id", "amount"
    )
    for st in settlements:
        amt = to_paisa(st["amount"])
        settled_out[st["payer_id"]] += amt
        settled_in[st["recipient_id"]] += amt
        debts[(st["payer_id"], st["recipient_id"])] -= amt

    # People who left the group but still appear in history
    involved = set(paid) | set(share) | set(settled_out) | set(settled_in)
    missing = involved - set(users)
    if missing:
        from users.models import User

        for u in User.objects.filter(pk__in=missing):
            users[u.pk] = u

    net = {}
    for uid in set(users):
        net[uid] = paid[uid] - share[uid] + settled_out[uid] - settled_in[uid]

    # Net the pairwise debts in both directions: A owes B 500, B owes A 200 -> A owes B 300
    pairwise = {}
    for (a, b) in list(debts):
        if (b, a) in pairwise or (a, b) in pairwise:
            continue
        diff = debts[(a, b)] - debts.get((b, a), 0)
        if diff > 0:
            pairwise[(a, b)] = diff
        elif diff < 0:
            pairwise[(b, a)] = -diff

    order = {uid: users[uid].full_name.lower() for uid in users}
    plan = minimize_transactions({u: n for u, n in net.items() if n != 0}, order=order)

    return GroupBalances(
        group=group,
        members=members,
        paid=dict(paid),
        share=dict(share),
        settled_out=dict(settled_out),
        settled_in=dict(settled_in),
        net=net,
        pairwise=pairwise,
        plan=plan,
        users=users,
        total_spent=sum(paid.values()),
    )


# ---------------------------------------------------------------------------
# Serialisation helpers (plain dicts for the API)
# ---------------------------------------------------------------------------

def user_brief(user, request=None):
    from users.serializers import picture_url

    return {
        "id": user.pk,
        "full_name": user.full_name,
        "profile_picture": picture_url(request, user),
    }


def plan_as_dicts(balances, request=None):
    return [
        {
            "from_user": user_brief(balances.users[frm], request),
            "to_user": user_brief(balances.users[to], request),
            "amount": from_paisa(amt),
        }
        for frm, to, amt in balances.plan
    ]


def balances_payload(balances, current_user, request=None):
    """Full response for GET /api/groups/{id}/balances/."""
    member_ids = {m.pk for m in balances.members}
    people = []
    for uid, user in balances.users.items():
        people.append({
            "user": user_brief(user, request),
            "is_member": uid in member_ids,
            "paid": from_paisa(balances.paid.get(uid, 0)),
            "share": from_paisa(balances.share.get(uid, 0)),
            "settlements_paid": from_paisa(balances.settled_out.get(uid, 0)),
            "settlements_received": from_paisa(balances.settled_in.get(uid, 0)),
            "net": from_paisa(balances.net_of(uid)),
            "status": "receive" if balances.net_of(uid) > 0 else "give" if balances.net_of(uid) < 0 else "settled",
        })
    people.sort(key=lambda p: (-p["net"], p["user"]["full_name"].lower()))

    me = current_user.pk
    give, receive = balances.plan_for(me)
    give_map = dict(give)
    receive_map = dict(receive)

    # Shared expenses between me and each other member
    shared = defaultdict(list)
    splits = (
        ExpenseSplit.objects.filter(expense__group=balances.group)
        .select_related("expense")
        .order_by("-expense__date", "-expense__created_at")
    )
    by_expense = defaultdict(dict)
    expenses = {}
    for s in splits:
        by_expense[s.expense_id][s.user_id] = s.amount
        expenses[s.expense_id] = s.expense
    for exp_id, parts in by_expense.items():
        exp = expenses[exp_id]
        payer = exp.paid_by_id
        if payer == me:
            for uid, amt in parts.items():
                if uid != me:
                    shared[uid].append((exp, "they_owe", amt))
        elif me in parts:
            shared[payer].append((exp, "you_owe", parts[me]))

    individual = []
    for uid, user in balances.users.items():
        if uid == me:
            continue
        direct = balances.pairwise.get((uid, me), 0) - balances.pairwise.get((me, uid), 0)
        items = shared.get(uid, [])
        if not (give_map.get(uid) or receive_map.get(uid) or direct or items):
            continue
        individual.append({
            "user": user_brief(user, request),
            "you_give": from_paisa(give_map.get(uid, 0)),
            "you_receive": from_paisa(receive_map.get(uid, 0)),
            "direct_net": from_paisa(direct),  # + they owe you / - you owe them (before optimisation)
            "shared_expenses": [
                {
                    "id": exp.pk,
                    "description": exp.description,
                    "category": exp.category,
                    "date": exp.date,
                    "total": exp.amount,
                    "direction": direction,
                    "amount": amt,
                }
                for exp, direction, amt in items[:10]
            ],
        })
    individual.sort(key=lambda i: (-(i["you_give"] + i["you_receive"]), i["user"]["full_name"].lower()))

    direct_count = count_direct_debts(balances.pairwise)
    return {
        "group_id": balances.group.pk,
        "total_spent": from_paisa(balances.total_spent),
        "my_net": from_paisa(balances.net_of(me)),
        "you_give": [{"user": user_brief(balances.users[u], request), "amount": from_paisa(a)} for u, a in give],
        "you_receive": [{"user": user_brief(balances.users[u], request), "amount": from_paisa(a)} for u, a in receive],
        "members": people,
        "individual": individual,
        "suggestions": plan_as_dicts(balances, request),
        "stats": {
            "direct_transactions": direct_count,
            "smart_transactions": len(balances.plan),
            "is_settled": not balances.plan,
        },
    }
