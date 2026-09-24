from django.contrib import admin

from .models import Activity, Notification


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ["description", "group", "action", "created_at"]
    list_filter = ["action"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "recipient", "kind", "is_read", "created_at"]
    list_filter = ["kind", "is_read"]
