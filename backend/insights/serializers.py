from decimal import Decimal

from rest_framework import serializers


class CategorySuggestionRequestSerializer(serializers.Serializer):
    """Input for POST /api/ml/suggest-category/."""

    description = serializers.CharField(max_length=120, allow_blank=True)
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal("0")
    )
