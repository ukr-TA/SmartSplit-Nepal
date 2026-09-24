from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework import serializers

from common.money import MAX_AMOUNT, from_paisa, to_paisa
from groups.models import Group, GroupMember
from users.serializers import UserSummarySerializer, picture_url

from .models import Expense, ExpenseSplit
from .splitting import SplitError, split_custom, split_equal, split_percentage

MAX_RECEIPT_BYTES = 5 * 1024 * 1024  # 5 MB


class ExpenseSplitSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)

    class Meta:
        model = ExpenseSplit
        fields = ["user", "amount", "percentage"]


class ExpenseSerializer(serializers.ModelSerializer):
    """Read representation."""

    group_name = serializers.CharField(source="group.name", read_only=True)
    paid_by = UserSummarySerializer(read_only=True)
    created_by = UserSummarySerializer(read_only=True)
    splits = ExpenseSplitSerializer(many=True, read_only=True)
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    receipt = serializers.SerializerMethodField()
    my_share = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = [
            "id", "group", "group_name", "description", "amount", "category", "category_label",
            "date", "paid_by", "split_method", "notes", "receipt", "splits", "my_share",
            "created_by", "created_at", "updated_at", "can_edit",
        ]

    def get_receipt(self, obj):
        if not obj.receipt:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.receipt.url) if request else obj.receipt.url

    def get_my_share(self, obj):
        user = self.context["request"].user
        for s in obj.splits.all():
            if s.user_id == user.pk:
                return s.amount
        return Decimal("0.00")

    def get_can_edit(self, obj):
        user = self.context["request"].user
        if user.pk in (obj.created_by_id, obj.paid_by_id):
            return True
        return GroupMember.objects.filter(group_id=obj.group_id, user=user, role=GroupMember.Role.OWNER).exists()


class SplitInputSerializer(serializers.Serializer):
    user = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, min_value=Decimal("0"))
    percentage = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, min_value=Decimal("0"))


class ExpenseWriteSerializer(serializers.ModelSerializer):
    """
    Create / update / preview input.

    equal      -> "participants": [user ids]
    custom     -> "splits": [{"user": id, "amount": "1500.00"}, ...]
    percentage -> "splits": [{"user": id, "percentage": "50"}, ...]
    """

    group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all())
    paid_by = serializers.IntegerField()
    participants = serializers.ListField(child=serializers.IntegerField(), required=False)
    splits = SplitInputSerializer(many=True, required=False)
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01"), max_value=MAX_AMOUNT
    )

    class Meta:
        model = Expense
        fields = [
            "group", "description", "amount", "category", "date", "paid_by",
            "split_method", "notes", "participants", "splits",
        ]

    def validate_description(self, value):
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError("Please describe the expense.")
        return value

    def validate_date(self, value):
        from datetime import timedelta

        from django.utils import timezone

        if value > timezone.localdate() + timedelta(days=1):
            raise serializers.ValidationError("The expense date cannot be in the future.")
        return value

    def validate_group(self, group):
        user = self.context["request"].user
        if not GroupMember.objects.filter(group=group, user=user).exists():
            raise serializers.ValidationError("You are not a member of this group.")
        if self.instance and self.instance.group_id != group.pk:
            raise serializers.ValidationError("An expense cannot be moved to another group.")
        return group

    def validate(self, attrs):
        instance = self.instance
        group = attrs.get("group") or (instance.group if instance else None)
        amount = attrs.get("amount", instance.amount if instance else None)
        method = attrs.get("split_method", instance.split_method if instance else Expense.SplitMethod.EQUAL)
        paid_by = attrs.get("paid_by", instance.paid_by_id if instance else None)

        member_ids = set(GroupMember.objects.filter(group=group).values_list("user_id", flat=True))
        if paid_by not in member_ids:
            raise serializers.ValidationError({"paid_by": "The payer must be a member of the group."})

        split_fields_given = "participants" in attrs or "splits" in attrs or "amount" in attrs \
            or "split_method" in attrs or instance is None
        if not split_fields_given:
            return attrs  # e.g. only the description changed

        total = to_paisa(amount)
        try:
            if method == Expense.SplitMethod.EQUAL:
                participants = attrs.get("participants")
                if participants is None and instance is not None:
                    participants = list(instance.splits.values_list("user_id", flat=True))
                participants = participants or []
                self._check_members(participants, member_ids)
                shares = split_equal(total, participants)
            elif method == Expense.SplitMethod.CUSTOM:
                rows = attrs.get("splits") or []
                if any("amount" not in r for r in rows):
                    raise SplitError("Enter an amount for every participant.")
                self._check_members([r["user"] for r in rows], member_ids)
                shares = split_custom(total, [(r["user"], to_paisa(r["amount"])) for r in rows])
            elif method == Expense.SplitMethod.PERCENTAGE:
                rows = attrs.get("splits") or []
                if any("percentage" not in r for r in rows):
                    raise SplitError("Enter a percentage for every participant.")
                self._check_members([r["user"] for r in rows], member_ids)
                shares = split_percentage(total, [(r["user"], Decimal(r["percentage"])) for r in rows])
            else:
                raise SplitError("Unknown split method.")
        except SplitError as exc:
            raise serializers.ValidationError({"splits": str(exc)})
        except InvalidOperation:
            raise serializers.ValidationError({"splits": "Invalid number in split."})

        attrs["_shares"] = shares
        return attrs

    @staticmethod
    def _check_members(user_ids, member_ids):
        outsiders = [uid for uid in user_ids if uid not in member_ids]
        if outsiders:
            raise SplitError("Every participant must be a member of the group.")

    def _save_splits(self, expense, shares):
        expense.splits.all().delete()
        ExpenseSplit.objects.bulk_create([
            ExpenseSplit(expense=expense, user_id=uid, amount=from_paisa(paisa), percentage=pct)
            for uid, paisa, pct in shares
        ])

    @transaction.atomic
    def create(self, validated_data):
        shares = validated_data.pop("_shares")
        validated_data.pop("participants", None)
        validated_data.pop("splits", None)
        validated_data["paid_by_id"] = validated_data.pop("paid_by")
        expense = Expense.objects.create(created_by=self.context["request"].user, **validated_data)
        self._save_splits(expense, shares)
        return expense

    @transaction.atomic
    def update(self, instance, validated_data):
        shares = validated_data.pop("_shares", None)
        validated_data.pop("participants", None)
        validated_data.pop("splits", None)
        validated_data.pop("group", None)
        if "paid_by" in validated_data:
            validated_data["paid_by_id"] = validated_data.pop("paid_by")
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if shares is not None:
            self._save_splits(instance, shares)
        return instance

    def preview(self):
        """Explain the split without saving (used by the Review step)."""
        from users.models import User

        data = self.validated_data
        shares = data["_shares"]
        users = {u.pk: u for u in User.objects.filter(pk__in=[s[0] for s in shares] + [data["paid_by"]])}
        request = self.context["request"]
        me = request.user.pk
        payer = users[data["paid_by"]]
        rows = []
        for uid, paisa, pct in shares:
            amount = from_paisa(paisa)
            rows.append({
                "user": {"id": uid, "full_name": users[uid].full_name,
                         "profile_picture": picture_url(request, users[uid])},
                "amount": amount,
                "percentage": pct,
                # what this expense does to this person's balance
                "balance_effect": (data["amount"] - amount) if uid == payer.pk else -amount,
            })
        payer_in = any(uid == payer.pk for uid, _, _ in shares)
        if not payer_in:
            rows.append({
                "user": {"id": payer.pk, "full_name": payer.full_name,
                         "profile_picture": picture_url(request, payer)},
                "amount": Decimal("0.00"),
                "percentage": None,
                "balance_effect": data["amount"],
                "not_participating": True,
            })
        my_share = next((r["amount"] for r in rows if r["user"]["id"] == me), Decimal("0.00"))
        my_effect = next((r["balance_effect"] for r in rows if r["user"]["id"] == me), Decimal("0.00"))
        return {
            "description": data["description"],
            "amount": data["amount"],
            "category": data.get("category", Expense.Category.OTHER),
            "date": data.get("date"),
            "split_method": data.get("split_method", Expense.SplitMethod.EQUAL),
            "paid_by": {"id": payer.pk, "full_name": payer.full_name},
            "shares": rows,
            "my_share": my_share,
            "my_balance_effect": my_effect,
        }


class ReceiptUploadSerializer(serializers.Serializer):
    receipt = serializers.ImageField()

    def validate_receipt(self, value):
        if value.size > MAX_RECEIPT_BYTES:
            raise serializers.ValidationError("Receipt image must be smaller than 5 MB.")
        return value
