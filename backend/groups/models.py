import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

# Letters/digits that are easy to read aloud and type (no 0/O, 1/I/L)
INVITE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
INVITE_TOKEN_LENGTH = 10
INVITE_VALID_DAYS = 7


class Group(models.Model):
    class GroupType(models.TextChoices):
        TRIP = "trip", "Trip"
        COLLEGE = "college", "College"
        FRIENDS = "friends", "Friends"
        ROOMMATES = "roommates", "Roommates"
        FAMILY = "family", "Family"
        CUSTOM = "custom", "Custom"

    name = models.CharField(max_length=80)
    description = models.CharField(max_length=300, blank=True)
    group_type = models.CharField(max_length=20, choices=GroupType.choices, default=GroupType.FRIENDS)
    is_trip = models.BooleanField(default=False, help_text="Enables Trip Mode dashboard and analytics")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_groups"
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="GroupMember", related_name="expense_groups"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__isnull=True) | Q(start_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="group_end_after_start",
            )
        ]

    def __str__(self):
        return self.name

    def is_member(self, user):
        return self.memberships.filter(user=user).exists()

    def is_owner(self, user):
        return self.memberships.filter(user=user, role=GroupMember.Role.OWNER).exists()


class GroupMember(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MEMBER = "member", "Member"

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["joined_at"]
        constraints = [
            models.UniqueConstraint(fields=["group", "user"], name="unique_group_member"),
        ]

    def __str__(self):
        return f"{self.user} in {self.group} ({self.role})"


def generate_invite_token():
    return "".join(secrets.choice(INVITE_ALPHABET) for _ in range(INVITE_TOKEN_LENGTH))


def default_invite_expiry():
    return timezone.now() + timedelta(days=INVITE_VALID_DAYS)


class GroupInvitation(models.Model):
    """A shareable join link / QR code for a group."""

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="invitations")
    token = models.CharField(max_length=32, unique=True, default=generate_invite_token, editable=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_invite_expiry)
    is_active = models.BooleanField(default=True)
    use_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.group} invite {self.token}"

    @property
    def is_valid(self):
        return self.is_active and self.expires_at > timezone.now()
