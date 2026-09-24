from decimal import Decimal

from rest_framework import serializers

from common.money import MAX_AMOUNT, format_npr, from_paisa, to_paisa
from groups.models import Group, GroupMember
from users.models import User
from users.serializers import UserSummarySerializer

from . import gateways
from .balances import calculate_group_balances
from .models import Settlement


class SettlementSerializer(serializers.ModelSerializer):
    payer = UserSummarySerializer(read_only=True)
    recipient = UserSummarySerializer(read_only=True)
    created_by = UserSummarySerializer(read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True)
    method_label = serializers.CharField(source="get_method_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    channel_label = serializers.CharField(source="get_channel_display", read_only=True)

    class Meta:
        model = Settlement
        fields = [
            "id", "group", "group_name", "payer", "recipient", "amount", "method", "method_label",
            "channel", "channel_label", "status", "status_label", "transaction_id",
            "gateway_reference", "note", "created_by", "created_at", "completed_at",
        ]
        read_only_fields = fields


class SettlementCreateSerializer(serializers.Serializer):
    group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all())
    recipient = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True))
    payer = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True), required=False,
        help_text="Defaults to you. Set it (cash only) when you are the recipient recording money you received.",
    )
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01"), max_value=MAX_AMOUNT
    )
    method = serializers.ChoiceField(choices=Settlement.Method.choices)
    channel = serializers.ChoiceField(
        choices=[Settlement.Channel.SIMULATION, Settlement.Channel.SANDBOX],
        required=False, default=Settlement.Channel.SIMULATION,
        help_text="For eSewa/Khalti: demo simulation or the real test gateway.",
    )
    note = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate(self, attrs):
        me = self.context["request"].user
        group = attrs["group"]
        payer = attrs.get("payer") or me
        recipient = attrs["recipient"]
        method = attrs["method"]
        amount = attrs["amount"]
        attrs["payer"] = payer

        member_ids = set(GroupMember.objects.filter(group=group).values_list("user_id", flat=True))
        if me.pk not in member_ids:
            raise serializers.ValidationError({"group": "You are not a member of this group."})
        if payer.pk not in member_ids or recipient.pk not in member_ids:
            raise serializers.ValidationError("Both people must be members of the group.")
        if payer.pk == recipient.pk:
            raise serializers.ValidationError("You cannot settle with yourself.")
        if me.pk not in (payer.pk, recipient.pk):
            raise serializers.ValidationError("You can only record settlements you paid or received.")
        if method != Settlement.Method.CASH and payer.pk != me.pk:
            raise serializers.ValidationError("Only the payer can pay through eSewa or Khalti.")

        # Keep settlements consistent with the balances
        balances = calculate_group_balances(group)
        owes = -balances.net_of(payer.pk)
        owed = balances.net_of(recipient.pk)
        if owes <= 0:
            who = "You don't" if payer.pk == me.pk else f"{payer.full_name} doesn't"
            raise serializers.ValidationError(f"{who} owe anything in this group.")
        if owed <= 0:
            raise serializers.ValidationError(f"{recipient.full_name} is not owed any money in this group.")
        limit = min(owes, owed)
        if to_paisa(amount) > limit:
            raise serializers.ValidationError(
                {"amount": f"The most that can be settled here is {format_npr(from_paisa(limit))}."}
            )

        if method == Settlement.Method.CASH:
            attrs["channel"] = Settlement.Channel.CASH
        elif attrs["channel"] == Settlement.Channel.SANDBOX:
            if method == Settlement.Method.ESEWA and not gateways.esewa_available():
                raise serializers.ValidationError("The eSewa test gateway is not configured.")
            if method == Settlement.Method.KHALTI:
                if not gateways.khalti_available():
                    raise serializers.ValidationError(
                        "The Khalti test gateway is not configured (KHALTI_SECRET_KEY is empty)."
                    )
                if amount < Decimal("10"):
                    raise serializers.ValidationError({"amount": "Khalti's minimum payment is Rs. 10."})
        return attrs
