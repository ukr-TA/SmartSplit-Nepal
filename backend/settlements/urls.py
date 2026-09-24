from django.urls import path
from rest_framework.routers import SimpleRouter

from .dashboard import DashboardView
from .views import PaymentConfigView, SettlementViewSet

router = SimpleRouter()
router.register("settlements", SettlementViewSet, basename="settlement")

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("payments/config/", PaymentConfigView.as_view(), name="payment-config"),
] + router.urls
