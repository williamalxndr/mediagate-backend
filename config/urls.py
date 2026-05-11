from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def api_home(_request):
    return JsonResponse({"message": "API is running"})


urlpatterns = [
    path("", api_home, name="api-home"),
    path("admin/", admin.site.urls),
    path("api/", include("config.api_urls")),
]

# MVP: Django serves uploaded media from MEDIA_ROOT. Swap to S3/CDN for scale.
urlpatterns += static(  # type: ignore[arg-type]
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
)
