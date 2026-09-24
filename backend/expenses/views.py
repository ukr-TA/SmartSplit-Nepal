from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from common.money import format_npr
from groups.models import Group, GroupMember
from notifications.models import Activity, Notification
from notifications.services import log_activity, notify

from .models import Expense
from .serializers import ExpenseSerializer, ExpenseWriteSerializer, ReceiptUploadSerializer


def _touch(group):
    Group.objects.filter(pk=group.pk).update(updated_at=timezone.now())


class ExpenseViewSet(viewsets.ModelViewSet):
    """
    /api/expenses/?group=<id>&category=food&search=hotel
    """

    http_method_names = ["get", "post", "patch", "delete", "options"]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        qs = (
            Expense.objects.filter(group__memberships__user=self.request.user)
            .select_related("group", "paid_by", "created_by")
            .prefetch_related("splits__user")
            .distinct()
        )
        params = self.request.query_params
        if params.get("group"):
            qs = qs.filter(group_id=params["group"])
        if params.get("category"):
            qs = qs.filter(category=params["category"])
        if params.get("search"):
            term = params["search"].strip()
            qs = qs.filter(Q(description__icontains=term) | Q(notes__icontains=term))
        if params.get("limit", "").isdigit():
            qs = qs[: int(params["limit"])]
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "partial_update", "preview"):
            return ExpenseWriteSerializer
        return ExpenseSerializer

    def _check_can_edit(self, expense):
        user = self.request.user
        if user.pk in (expense.created_by_id, expense.paid_by_id):
            return
        if GroupMember.objects.filter(group=expense.group, user=user, role=GroupMember.Role.OWNER).exists():
            return
        raise PermissionDenied("Only the person who added or paid this expense (or the group owner) can change it.")

    def _read(self, expense, code=status.HTTP_200_OK):
        expense = self.get_queryset().model.objects.select_related("group", "paid_by", "created_by") \
            .prefetch_related("splits__user").get(pk=expense.pk)
        return Response(ExpenseSerializer(expense, context=self.get_serializer_context()).data, status=code)

    def create(self, request, *args, **kwargs):
        serializer = ExpenseWriteSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        expense = serializer.save()
        actor = request.user
        group = expense.group
        log_activity(group, actor, Activity.Action.EXPENSE_ADDED,
                     f"{actor.full_name} added {expense.description}", amount=expense.amount)
        for split in expense.splits.select_related("user"):
            if split.user_id == actor.pk:
                continue
            if split.user_id == expense.paid_by_id:
                message = f"{expense.description} · {format_npr(expense.amount)} · You paid, your share {format_npr(split.amount)}"
            else:
                message = f"{expense.description} · {format_npr(expense.amount)} · You owe {format_npr(split.amount)}"
            notify([split.user], Notification.Kind.EXPENSE, f"{actor.full_name} added an expense",
                   message, group=group)
        _touch(group)
        return self._read(expense, status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        expense = self.get_object()
        self._check_can_edit(expense)
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        data.setdefault("group", expense.group_id)
        if "paid_by" not in data:
            data["paid_by"] = expense.paid_by_id
        serializer = ExpenseWriteSerializer(expense, data=data, partial=True, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        expense = serializer.save()
        log_activity(expense.group, request.user, Activity.Action.EXPENSE_UPDATED,
                     f"{request.user.full_name} edited {expense.description}", amount=expense.amount)
        _touch(expense.group)
        return self._read(expense)

    def destroy(self, request, *args, **kwargs):
        expense = self.get_object()
        self._check_can_edit(expense)
        group = expense.group
        log_activity(group, request.user, Activity.Action.EXPENSE_DELETED,
                     f"{request.user.full_name} deleted {expense.description}", amount=expense.amount)
        if expense.receipt:
            expense.receipt.delete(save=False)
        expense.delete()
        _touch(group)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"])
    def preview(self, request):
        """Validate and calculate shares without saving (Quick Split review step)."""
        serializer = ExpenseWriteSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        return Response(serializer.preview())

    @action(detail=True, methods=["post", "delete"], parser_classes=[MultiPartParser, FormParser, JSONParser])
    def receipt(self, request, pk=None):
        expense = self.get_object()
        if request.method == "DELETE":
            self._check_can_edit(expense)
            if expense.receipt:
                expense.receipt.delete(save=True)
            return self._read(expense)
        if request.user.pk not in (expense.created_by_id, expense.paid_by_id):
            self._check_can_edit(expense)
        serializer = ReceiptUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if expense.receipt:
            expense.receipt.delete(save=False)
        expense.receipt = serializer.validated_data["receipt"]
        expense.save(update_fields=["receipt", "updated_at"])
        return self._read(expense)
