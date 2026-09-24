from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Simple endpoint the frontend calls to confirm the API is reachable."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT version()")
        # e.g. "PostgreSQL 16.4 (Homebrew) on ..." -> "PostgreSQL 16.4"
        db_version = " ".join(cursor.fetchone()[0].split()[:2])

    return Response({
        "status": "ok",
        "app": "SmartSplit Nepal API",
        "tagline": "Split less. Settle smarter.",
        "database": db_version,
        "server_time": timezone.localtime().isoformat(),
    })


admin.site.site_header = "SmartSplit Nepal admin"
admin.site.site_title = "SmartSplit admin"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/", include("users.urls")),
    path("api/", include("groups.urls")),
    path("api/", include("expenses.urls")),
    path("api/", include("settlements.urls")),
    path("api/", include("insights.urls")),
    path("api/", include("notifications.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
