from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from groups.models import Group


class Expense(models.Model):
    class Category(models.TextChoices):
        FOOD = "food", "Food"
        TRANSPORT = "transport", "Transport"
        HOTEL = "hotel", "Hotel"
        ENTERTAINMENT = "entertainment", "Entertainment"
        SHOPPING = "shopping", "Shopping"
        EDUCATION = "education", "Education"
        UTILITIES = "utilities", "Utilities"
        RENT = "rent", "Rent"
        OTHER = "other", "Other"

    class SplitMethod(models.TextChoices):
        EQUAL = "equal", "Equal"
        CUSTOM = "custom", "Custom amounts"
        PERCENTAGE = "percentage", "Percentage"

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="expenses")
    description = models.CharField(max_length=120)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    date = models.DateField(default=timezone.localdate)
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="expenses_paid"
    )
    split_method = models.CharField(max_length=12, choices=SplitMethod.choices, default=SplitMethod.EQUAL)
    notes = models.TextField(blank=True, max_length=1000)
    receipt = models.ImageField(upload_to="receipts/%Y/%m/", blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="expenses_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["group", "date"])]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="expense_amount_positive"),
        ]

    def __str__(self):
        return f"{self.description} (Rs. {self.amount})"


class ExpenseSplit(models.Model):
    """How much of one expense a single participant is responsible for."""

    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="splits")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="expense_splits")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["expense", "user"], name="unique_expense_participant"),
            models.CheckConstraint(condition=Q(amount__gte=0), name="split_amount_not_negative"),
        ]

    def __str__(self):
        return f"{self.user} owes Rs. {self.amount} for {self.expense}"
