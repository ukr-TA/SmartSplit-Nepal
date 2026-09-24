from django.conf import settings
from django.db import models

from groups.models import Group


class Activity(models.Model):
    """Timeline entry visible to every member of a group."""

    class Action(models.TextChoices):
        GROUP_CREATED = "group_created", "Group created"
        GROUP_UPDATED = "group_updated", "Group updated"
        MEMBER_ADDED = "member_added", "Member added"
        MEMBER_JOINED = "member_joined", "Member joined"
        MEMBER_REMOVED = "member_removed", "Member removed"
        MEMBER_LEFT = "member_left", "Member left"
        EXPENSE_ADDED = "expense_added", "Expense added"
        EXPENSE_UPDATED = "expense_updated", "Expense updated"
        EXPENSE_DELETED = "expense_deleted", "Expense deleted"
        SETTLEMENT = "settlement", "Settlement"

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="activities")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="activities"
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name_plural = "activities"

    def __str__(self):
        return self.description


class Notification(models.Model):
    class Kind(models.TextChoices):
        EXPENSE = "expense", "Expense added"
        SETTLEMENT = "settlement", "Settlement received"
        MEMBER = "member", "Member joined"
        GROUP = "group", "Added to group"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=120)
    message = models.CharField(max_length=255)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True, related_name="+")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["recipient", "is_read"])]

    def __str__(self):
        return f"{self.recipient}: {self.title}"
