from rest_framework import serializers

from users.serializers import UserSummarySerializer

from .models import Group, GroupInvitation, GroupMember


class GroupMemberSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)

    class Meta:
        model = GroupMember
        fields = ["id", "user", "role", "joined_at"]


class GroupSerializer(serializers.ModelSerializer):
    """Used for list, create and update."""

    member_count = serializers.SerializerMethodField()
    members_preview = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()
    my_net = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()
    expense_count = serializers.SerializerMethodField()
    member_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False,
        help_text="Optional: users to add when creating the group",
    )

    class Meta:
        model = Group
        fields = [
            "id", "name", "description", "group_type", "is_trip", "start_date", "end_date",
            "created_at", "updated_at", "member_count", "members_preview", "my_role",
            "my_net", "total_spent", "expense_count", "member_ids",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    # Balances are pre-computed by the view and passed in context to avoid repeats
    def _balances(self, obj):
        cache = self.context.setdefault("_balances", {})
        if obj.pk not in cache:
            from settlements.balances import calculate_group_balances

            cache[obj.pk] = calculate_group_balances(obj)
        return cache[obj.pk]

    def get_member_count(self, obj):
        return len(self._balances(obj).members)

    def get_members_preview(self, obj):
        members = self._balances(obj).members[:5]
        return UserSummarySerializer(members, many=True, context=self.context).data

    def get_my_role(self, obj):
        user = self.context["request"].user
        for m in obj.memberships.all():
            if m.user_id == user.pk:
                return m.role
        return None

    def get_my_net(self, obj):
        from common.money import from_paisa

        return from_paisa(self._balances(obj).net_of(self.context["request"].user.pk))

    def get_total_spent(self, obj):
        from common.money import from_paisa

        return from_paisa(self._balances(obj).total_spent)

    def get_expense_count(self, obj):
        return obj.expenses.count()

    def validate_name(self, value):
        value = " ".join(value.split())
        if len(value) < 2:
            raise serializers.ValidationError("Group name must have at least 2 characters.")
        return value

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "End date cannot be before the start date."})
        # Choosing the Trip type switches Trip Mode on automatically
        if attrs.get("group_type") == Group.GroupType.TRIP:
            attrs["is_trip"] = True
        return attrs


class GroupDetailSerializer(GroupSerializer):
    members = serializers.SerializerMethodField()

    class Meta(GroupSerializer.Meta):
        fields = GroupSerializer.Meta.fields + ["members", "created_by"]
        read_only_fields = GroupSerializer.Meta.read_only_fields + ["created_by"]

    def get_members(self, obj):
        qs = obj.memberships.select_related("user").all()
        return GroupMemberSerializer(qs, many=True, context=self.context).data


class InvitationSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = GroupInvitation
        fields = ["token", "group", "group_name", "created_at", "expires_at", "is_valid", "use_count"]
        read_only_fields = fields


class AddMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
