"""URL configuration for Sakay.ph.

Phase 3 mounts each app's API under /api/ as its step lands. Step 3.01 wires
accounts (register, login, refresh, me, OTP).
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.accounts.urls")),
]
