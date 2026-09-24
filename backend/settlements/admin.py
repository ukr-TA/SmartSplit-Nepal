from django.contrib import admin

from .models import Settlement


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ["transaction_id", "group", "payer", "recipient", "amount", "method", "channel", "status", "created_at"]
    list_filter = ["method", "channel", "status"]
    search_fields = ["transaction_id", "gateway_reference"]
