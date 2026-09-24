from django.contrib import admin

from .models import Expense, ExpenseSplit


class SplitInline(admin.TabularInline):
    model = ExpenseSplit
    extra = 0


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["description", "group", "amount", "category", "paid_by", "split_method", "date"]
    list_filter = ["category", "split_method"]
    search_fields = ["description"]
    inlines = [SplitInline]
