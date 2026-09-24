from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Activity, Notification
from .serializers import ActivitySerializer, NotificationSerializer


class NotificationViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """GET /api/notifications/  PATCH /api/notifications/{id}/ {"is_read": true}"""

    serializer_class = NotificationSerializer
    http_method_names = ["get", "patch", "post", "options"]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).select_related("group")

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return Response({
            "unread_count": qs.filter(is_read=False).count(),
            "results": NotificationSerializer(qs[:50], many=True).data,
        })

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"updated": updated})


class MyActivityView(APIView):
    """Activity across all of the user's groups: GET /api/activity/"""

    def get(self, request):
        qs = (
            Activity.objects.filter(group__memberships__user=request.user)
            .select_related("actor", "group")
            .distinct()[:100]
        )
        return Response(ActivitySerializer(qs, many=True, context={"request": request}).data)
