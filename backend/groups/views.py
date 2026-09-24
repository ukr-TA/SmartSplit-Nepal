from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.money import format_npr, from_paisa
from insights.predictor import forecast_group_spending, monthly_history
from notifications.models import Activity, Notification
from notifications.serializers import ActivitySerializer
from notifications.services import log_activity, notify
from settlements.balances import balances_payload, calculate_group_balances, plan_as_dicts
from users.models import User

from .analytics import group_analytics
from .models import Group, GroupInvitation, GroupMember
from .permissions import IsGroupMember, is_owner
from .serializers import (
    AddMemberSerializer,
    GroupDetailSerializer,
    GroupSerializer,
    InvitationSerializer,
)


def add_member(group, user, actor, via_invite=False, notify_others=True):
    """Add `user` to `group`, log it and notify. Returns the membership (or None if already in)."""
    membership, created = GroupMember.objects.get_or_create(group=group, user=user)
    if not created:
        return None
    others = [m.user for m in group.memberships.select_related("user") if m.user_id != user.pk]
    if via_invite:
        log_activity(group, user, Activity.Action.MEMBER_JOINED, f"{user.full_name} joined the group")
        notify(others, Notification.Kind.MEMBER, "New member joined",
               f"{user.full_name} joined {group.name}", group=group)
    else:
        log_activity(group, actor, Activity.Action.MEMBER_ADDED,
                     f"{actor.full_name} added {user.full_name}")
        notify([user], Notification.Kind.GROUP, "You were added to a group",
               f"{actor.full_name} added you to {group.name}", group=group)
        if notify_others:
            notify(others, Notification.Kind.MEMBER, "New member joined",
                   f"{user.full_name} joined {group.name}", group=group, exclude=actor)
    Group.objects.filter(pk=group.pk).update(updated_at=timezone.now())
    return membership


class GroupViewSet(viewsets.ModelViewSet):
    """
    /api/groups/                 list, create
    /api/groups/{id}/            retrieve, update (owner), delete (owner, settled only)
    plus the extra actions below.
    """

    permission_classes = [IsAuthenticated, IsGroupMember]
    http_method_names = ["get", "post", "patch", "delete", "options"]

    def get_queryset(self):
        return (
            Group.objects.filter(memberships__user=self.request.user)
            .prefetch_related("memberships")
            .distinct()
        )

    def get_serializer_class(self):
        if self.action in ("retrieve", "partial_update", "create"):
            return GroupDetailSerializer
        return GroupSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        member_ids = serializer.validated_data.pop("member_ids", [])
        group = serializer.save(created_by=user)
        GroupMember.objects.create(group=group, user=user, role=GroupMember.Role.OWNER)
        log_activity(group, user, Activity.Action.GROUP_CREATED, f"{user.full_name} created {group.name}")
        for new_user in User.objects.filter(pk__in=member_ids, is_active=True).exclude(pk=user.pk):
            add_member(group, new_user, user, notify_others=False)

    def partial_update(self, request, *args, **kwargs):
        if not is_owner(self.get_object(), request.user):
            raise PermissionDenied("Only the group owner can edit the group.")
        return super().partial_update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.validated_data.pop("member_ids", None)
        group = serializer.save()
        log_activity(group, self.request.user, Activity.Action.GROUP_UPDATED,
                     f"{self.request.user.full_name} updated group details")

    def destroy(self, request, *args, **kwargs):
        group = self.get_object()
        if not is_owner(group, request.user):
            raise PermissionDenied("Only the group owner can delete the group.")
        balances = calculate_group_balances(group)
        if balances.plan:
            raise ValidationError(
                "This group still has unsettled balances. Settle up before deleting it."
            )
        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ---- members -----------------------------------------------------------
    @action(detail=True, methods=["post"], url_path="members")
    def add_member(self, request, pk=None):
        group = self.get_object()
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_object_or_404(User, pk=serializer.validated_data["user_id"], is_active=True)
        if add_member(group, user, request.user) is None:
            raise ValidationError(f"{user.full_name} is already a member of this group.")
        return Response(GroupDetailSerializer(group, context={"request": request}).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"members/(?P<member_id>\d+)")
    def remove_member(self, request, pk=None, member_id=None):
        """member_id is the user's id. Owners can remove anyone; members can remove themselves."""
        group = self.get_object()
        membership = get_object_or_404(GroupMember, group=group, user_id=member_id)
        leaving_self = membership.user_id == request.user.pk
        if not leaving_self and not is_owner(group, request.user):
            raise PermissionDenied("Only the group owner can remove members.")
        if membership.role == GroupMember.Role.OWNER:
            raise ValidationError("The group owner cannot be removed.")
        net = calculate_group_balances(group).net_of(membership.user_id)
        if net != 0:
            word = "receive" if net > 0 else "pay"
            raise ValidationError(
                f"{membership.user.full_name} still has to {word} {format_npr(from_paisa(abs(net)))}. "
                "Settle their balance first."
            )
        name = membership.user.full_name
        membership.delete()
        if leaving_self:
            log_activity(group, request.user, Activity.Action.MEMBER_LEFT, f"{name} left the group")
        else:
            log_activity(group, request.user, Activity.Action.MEMBER_REMOVED,
                         f"{request.user.full_name} removed {name}")
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ---- invitations -------------------------------------------------------
    @action(detail=True, methods=["post"], url_path="invite")
    def invite(self, request, pk=None):
        """Return the group's active invite (creating one if needed). {"regenerate": true} makes a new one."""
        group = self.get_object()
        active = group.invitations.filter(is_active=True).first()
        if request.data.get("regenerate") and active:
            group.invitations.filter(is_active=True).update(is_active=False)
            active = None
        if active is None or not active.is_valid:
            active = GroupInvitation.objects.create(group=group, created_by=request.user)
        return Response(InvitationSerializer(active).data, status=status.HTTP_200_OK)

    # ---- money views -------------------------------------------------------
    @action(detail=True, methods=["get"])
    def balances(self, request, pk=None):
        group = self.get_object()
        return Response(balances_payload(calculate_group_balances(group), request.user, request))

    @action(detail=True, methods=["get"], url_path="settlement-suggestions")
    def settlement_suggestions(self, request, pk=None):
        group = self.get_object()
        balances = calculate_group_balances(group)
        return Response({
            "group_id": group.pk,
            "suggestions": plan_as_dicts(balances, request),
            "direct_transactions": sum(1 for v in balances.pairwise.values() if v > 0),
            "smart_transactions": len(balances.plan),
        })

    @action(detail=True, methods=["get"])
    def activity(self, request, pk=None):
        group = self.get_object()
        qs = group.activities.select_related("actor")[:100]
        return Response(ActivitySerializer(qs, many=True, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def analytics(self, request, pk=None):
        group = self.get_object()
        return Response(group_analytics(group, calculate_group_balances(group), request))

    @action(detail=True, methods=["get"])
    def forecast(self, request, pk=None):
        """Predicted total spending for this group next month (machine-learning model).

        The model is trained in ml/notebooks/smartsplit_ml.ipynb. If its artefact is missing,
        the response falls back to the average of the last three months and says so.
        """
        group = self.get_object()
        rows = list(group.expenses.values_list("date", "amount", "category"))
        history = monthly_history(rows)
        payload = forecast_group_spending(history, group.group_type, today=timezone.localdate())
        payload["group_type"] = group.group_type
        return Response(payload)


class JoinGroupView(APIView):
    """GET: preview an invite. POST: join the group."""

    permission_classes = [IsAuthenticated]

    def _invite(self, token):
        invite = GroupInvitation.objects.select_related("group").filter(token=token.strip().upper()).first()
        if not invite or not invite.is_valid:
            raise ValidationError("This invitation link is invalid or has expired. Ask for a new one.")
        return invite

    def get(self, request, token):
        invite = self._invite(token)
        group = invite.group
        return Response({
            "token": invite.token,
            "group": {
                "id": group.pk,
                "name": group.name,
                "description": group.description,
                "group_type": group.group_type,
                "is_trip": group.is_trip,
                "member_count": group.memberships.count(),
            },
            "invited_by": invite.created_by.full_name,
            "already_member": group.is_member(request.user),
            "expires_at": invite.expires_at,
        })

    @transaction.atomic
    def post(self, request, token):
        invite = self._invite(token)
        group = invite.group
        if add_member(group, request.user, invite.created_by, via_invite=True) is None:
            return Response({"group_id": group.pk, "joined": False, "detail": "You are already a member."})
        GroupInvitation.objects.filter(pk=invite.pk).update(use_count=F("use_count") + 1)
        return Response({"group_id": group.pk, "joined": True}, status=status.HTTP_201_CREATED)
