import json

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import predictor
from .serializers import CategorySuggestionRequestSerializer


class SuggestCategoryView(APIView):
    """Suggest a category for an expense description.

    POST /api/ml/suggest-category/
        {"description": "Momo at Everest Momo Center", "amount": 450}
    ->  {"category": "food", "confidence": 0.93,
         "alternatives": [{"category": "entertainment", "confidence": 0.03}],
         "source": "model"}

    The response is a *suggestion*: the client preselects it but the user stays in control.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CategorySuggestionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        amount = serializer.validated_data.get("amount")
        result = predictor.suggest_category(
            serializer.validated_data["description"],
            float(amount) if amount is not None else None,
        )
        return Response(result)


class ModelInfoView(APIView):
    """What the running server knows about the trained models.

    Used by the UI to decide whether to show the 'suggested category' hint at all, and handy
    when marking the project: it reports the metrics recorded by the notebook.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        metrics_path = predictor.models_dir() / "metrics.json"
        metrics = None
        if metrics_path.exists():
            try:
                metrics = json.loads(metrics_path.read_text())
            except (OSError, json.JSONDecodeError):
                metrics = None

        classifier = predictor._load("classifier")  # noqa: SLF001 - internal by design
        forecaster = predictor._load("forecaster")  # noqa: SLF001

        payload = {
            "classifier_available": classifier is not None,
            "forecaster_available": forecaster is not None,
            "categories": predictor.CATEGORIES,
            "min_forecast_months": predictor.MIN_FORECAST_MONTHS,
        }
        if metrics:
            payload["classifier"] = {
                "model": metrics["classifier"]["selected_model"],
                "test_accuracy": metrics["classifier"]["test_accuracy"],
                "test_macro_f1": metrics["classifier"]["test_macro_f1"],
            }
            payload["forecaster"] = {"model": metrics["forecaster"]["selected_model"]}
            payload["dataset"] = metrics["dataset"]
        return Response(payload, status=status.HTTP_200_OK)
