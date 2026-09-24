import secrets

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from groups.models import Group

TX_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


class Settlement(models.Model):
    """A payment from one group member to another that reduces their balance."""

    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        ESEWA = "esewa", "eSewa"
        KHALTI = "khalti", "Khalti"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESSFUL = "successful", "Successful"
        FAILED = "failed", "Failed"

    class Channel(models.TextChoices):
        CASH = "cash", "Recorded manually"
        SIMULATION = "simulation", "Demo simulation"
        SANDBOX = "sandbox", "Gateway test environment"

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="settlements")
    payer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="settlements_paid")
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="settlements_received"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=10, choices=Method.choices)
    channel = models.CharField(max_length=12, choices=Channel.choices, default=Channel.CASH)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    transaction_id = models.CharField(max_length=40, unique=True, editable=False)
    gateway_reference = models.CharField(
        max_length=100, blank=True, help_text="eSewa transaction_code / Khalti pidx or transaction_id"
    )
    note = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="settlements_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="settlement_amount_positive"),
            models.CheckConstraint(condition=~Q(payer=F("recipient")), name="settlement_not_to_self"),
        ]

    def __str__(self):
        return f"{self.transaction_id}: {self.payer} -> {self.recipient} Rs. {self.amount} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id(self.method)
        super().save(*args, **kwargs)

    @classmethod
    def generate_transaction_id(cls, method):
        """e.g. SMRT-KHL-20260916-X82K9  (unique, human-readable)."""
        prefix = {"cash": "CSH", "esewa": "ESW", "khalti": "KHL"}.get(method, "TXN")
        date = timezone.localdate().strftime("%Y%m%d")
        while True:
            suffix = "".join(secrets.choice(TX_ALPHABET) for _ in range(5))
            tx_id = f"SMRT-{prefix}-{date}-{suffix}"
            if not cls.objects.filter(transaction_id=tx_id).exists():
                return tx_id

    def mark_successful(self, reference=""):
        self.status = self.Status.SUCCESSFUL
        self.completed_at = timezone.now()
        if reference:
            self.gateway_reference = reference
        self.save(update_fields=["status", "completed_at", "gateway_reference"])

    def mark_failed(self, reference=""):
        self.status = self.Status.FAILED
        self.completed_at = timezone.now()
        if reference:
            self.gateway_reference = reference
        self.save(update_fields=["status", "completed_at", "gateway_reference"])
