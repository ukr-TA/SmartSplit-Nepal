from decimal import Decimal

from django.db.models import Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from common.money import from_paisa
from expenses.models import Expense
from groups.models import Group
from notifications.models import Activity
from notifications.serializers import ActivitySerializer

from .balances import calculate_group_balances, user_brief
from .models import Settlement
from .serializers import SettlementSerializer


class DashboardView(APIView):
    """
    GET /api/dashboard/ - everything the home screen needs in one request:
    totals, per-group positions, what to pay / receive, and recent activity.
    """

    def get(self, request):
        me = request.user
        groups = list(Group.objects.filter(memberships__user=me).distinct().order_by("-updated_at"))

        total_give = total_receive = 0
        should_pay, should_receive, group_cards = [], [], []

        for group in groups:
            balances = calculate_group_balances(group)
            give, receive = balances.plan_for(me.pk)
            for uid, amt in give:
                total_give += amt
                should_pay.append({
                    "group": {"id": group.pk, "name": group.name},
                    "user": user_brief(balances.users[uid], request),
                    "amount": from_paisa(amt),
                })
            for uid, amt in receive:
                total_receive += amt
                should_receive.append({
                    "group": {"id": group.pk, "name": group.name},
                    "user": user_brief(balances.users[uid], request),
                    "amount": from_paisa(amt),
                })
            group_cards.append({
                "id": group.pk,
                "name": group.name,
                "group_type": group.group_type,
                "is_trip": group.is_trip,
                "member_count": len(balances.members),
                "total_spent": from_paisa(balances.total_spent),
                "my_net": from_paisa(balances.net_of(me.pk)),
                "updated_at": group.updated_at,
            })

        should_pay.sort(key=lambda r: -r["amount"])
        should_receive.sort(key=lambda r: -r["amount"])

        group_ids = [g.pk for g in groups]
        recent_expenses = (
            Expense.objects.filter(group_id__in=group_ids)
            .select_related("group", "paid_by")
            .prefetch_related("splits")
            .order_by("-date", "-created_at")[:6]
        )
        expenses_data = []
        for e in recent_expenses:
            my_share = next((s.amount for s in e.splits.all() if s.user_id == me.pk), Decimal("0.00"))
            expenses_data.append({
                "id": e.pk,
                "description": e.description,
                "category": e.category,
                "amount": e.amount,
                "date": e.date,
                "group": {"id": e.group_id, "name": e.group.name},
                "paid_by": user_brief(e.paid_by, request),
                "my_share": my_share,
                "participant_count": len(e.splits.all()),
            })

        recent_settlements = (
            Settlement.objects.filter(group_id__in=group_ids, status=Settlement.Status.SUCCESSFUL)
            .filter(Q(payer=me) | Q(recipient=me))
            .select_related("group", "payer", "recipient", "created_by")[:5]
        )
        activity = (
            Activity.objects.filter(group_id__in=group_ids)
            .select_related("actor", "group")[:8]
        )
        month_start = timezone.localdate().replace(day=1)
        my_month_spend = sum(
            (s.amount for e in Expense.objects.filter(group_id__in=group_ids, date__gte=month_start)
             .prefetch_related("splits") for s in e.splits.all() if s.user_id == me.pk),
            Decimal("0.00"),
        )

        return Response({
            "user": {"id": me.pk, "full_name": me.full_name},
            "summary": {
                "you_owe": from_paisa(total_give),
                "you_are_owed": from_paisa(total_receive),
                "net_balance": from_paisa(total_receive - total_give),
                "active_groups": len(groups),
                "my_spending_this_month": my_month_spend,
            },
            "should_pay": should_pay,
            "should_receive": should_receive,
            "groups": group_cards,
            "recent_expenses": expenses_data,
            "recent_settlements": SettlementSerializer(recent_settlements, many=True,
                                                       context={"request": request}).data,
            "recent_activity": ActivitySerializer(activity, many=True, context={"request": request}).data,
        })
