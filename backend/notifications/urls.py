from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import MyActivityView, NotificationViewSet

router = SimpleRouter()
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("activity/", MyActivityView.as_view(), name="my-activity"),
] + router.urls
