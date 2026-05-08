from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("config.api_urls")),
]

# MVP: Django serves uploaded media from MEDIA_ROOT. Swap to S3/CDN for scale.
urlpatterns += static(  # type: ignore[arg-type]
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
)
