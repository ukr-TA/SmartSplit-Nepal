from rest_framework.permissions import BasePermission

from .models import GroupMember


class IsGroupMember(BasePermission):
    message = "You are not a member of this group."

    def has_object_permission(self, request, view, obj):
        return GroupMember.objects.filter(group=obj, user=request.user).exists()


def is_owner(group, user):
    return GroupMember.objects.filter(group=group, user=user, role=GroupMember.Role.OWNER).exists()
