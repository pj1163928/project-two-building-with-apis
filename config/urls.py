"""Root URLs. Each app has its own namespace."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("catalog.urls")),
    path("", include("packs.urls")),
]
