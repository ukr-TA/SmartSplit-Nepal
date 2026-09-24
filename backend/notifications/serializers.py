from rest_framework import serializers

from users.serializers import UserSummarySerializer

from .models import Activity, Notification


class ActivitySerializer(serializers.ModelSerializer):
    actor = UserSummarySerializer(read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True)

    class Meta:
        model = Activity
        fields = ["id", "group", "group_name", "actor", "action", "description", "amount", "created_at"]


class NotificationSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True, default=None)

    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "message", "group", "group_name", "is_read", "created_at"]
        read_only_fields = ["id", "kind", "title", "message", "group", "group_name", "created_at"]
