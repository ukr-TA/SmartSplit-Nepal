"""Trip / group spending analytics."""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum

from common.money import from_paisa
from expenses.models import Expense

MAX_DAILY_POINTS = 62


def _pct(part, total):
    if not total:
        return Decimal("0")
    return (Decimal(part) * 100 / Decimal(total)).quantize(Decimal("0.1"))


def group_analytics(group, balances, request=None):
    from settlements.balances import user_brief

    expenses = Expense.objects.filter(group=group)
    total = expenses.aggregate(t=Sum("amount"))["t"] or Decimal("0")
    count = expenses.count()
    labels = dict(Expense.Category.choices)

    by_category = [
        {
            "category": row["category"],
            "label": labels.get(row["category"], row["category"]),
            "amount": row["amount"],
            "count": row["n"],
            "percentage": _pct(row["amount"], total),
        }
        for row in expenses.values("category").annotate(amount=Sum("amount"), n=Count("id")).order_by("-amount")
    ]

    by_member = sorted(
        (
            {
                "user": user_brief(user, request),
                "paid": from_paisa(balances.paid.get(uid, 0)),
                "share": from_paisa(balances.share.get(uid, 0)),
                "paid_percentage": _pct(balances.paid.get(uid, 0), balances.total_spent),
            }
            for uid, user in balances.users.items()
        ),
        key=lambda r: (-r["paid"], r["user"]["full_name"].lower()),
    )

    per_day = {
        row["date"]: row["amount"]
        for row in expenses.values("date").annotate(amount=Sum("amount")).order_by("date")
    }

    # Date range: trip dates if set, otherwise first -> last expense
    start = group.start_date or (min(per_day) if per_day else None)
    end = group.end_date or (max(per_day) if per_day else None)
    if per_day:
        start = min(start, min(per_day))
        end = max(end, max(per_day))

    daily = []
    if start and end:
        days = (end - start).days + 1
        if days <= MAX_DAILY_POINTS:
            daily = [
                {"date": start + timedelta(days=i), "amount": per_day.get(start + timedelta(days=i), Decimal("0"))}
                for i in range(days)
            ]
        else:
            daily = [{"date": d, "amount": a} for d, a in sorted(per_day.items())]
    trip_days = (end - start).days + 1 if start and end else 0

    top = expenses.select_related("paid_by").order_by("-amount")[:3]

    member_count = len(balances.members) or 1
    return {
        "group_id": group.pk,
        "name": group.name,
        "is_trip": group.is_trip,
        "start_date": group.start_date,
        "end_date": group.end_date,
        "days": trip_days,
        "total_spent": total,
        "expense_count": count,
        "member_count": len(balances.members),
        "average_per_day": (total / trip_days).quantize(Decimal("0.01")) if trip_days else Decimal("0"),
        "average_per_person": (total / member_count).quantize(Decimal("0.01")),
        "by_category": by_category,
        "by_member": by_member,
        "daily": daily,
        "highest_day": max(daily, key=lambda d: d["amount"]) if daily and total else None,
        "top_expenses": [
            {
                "id": e.pk,
                "description": e.description,
                "category": e.category,
                "amount": e.amount,
                "date": e.date,
                "paid_by": e.paid_by.full_name,
            }
            for e in top
        ],
    }
