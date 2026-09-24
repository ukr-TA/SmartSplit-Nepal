from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import GroupViewSet, JoinGroupView

router = SimpleRouter()
router.register("groups", GroupViewSet, basename="group")

urlpatterns = [
    # must come before the router so "join" isn't treated as a group id
    path("groups/join/<str:token>/", JoinGroupView.as_view(), name="group-join"),
] + router.urls
