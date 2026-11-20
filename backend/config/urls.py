"""URL configuration for Sakay.ph.

Phase 3 mounts each app's API under /api/ as its step lands. Step 3.01 wired
accounts (register, login, refresh, me, OTP); Step 3.02 adds the schema and
the ride-domain read/write endpoints.
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.rides.urls")),
]