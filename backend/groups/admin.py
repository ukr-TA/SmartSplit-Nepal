from django.contrib import admin

from .models import Group, GroupInvitation, GroupMember


class MemberInline(admin.TabularInline):
    model = GroupMember
    extra = 0


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ["name", "group_type", "is_trip", "created_by", "created_at"]
    list_filter = ["group_type", "is_trip"]
    search_fields = ["name"]
    inlines = [MemberInline]


@admin.register(GroupInvitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ["token", "group", "created_by", "expires_at", "is_active", "use_count"]
