from django.contrib import admin

from .models import PlatformConfig


@admin.register(PlatformConfig)
class PlatformConfigAdmin(admin.ModelAdmin):
    list_display = ["key", "value", "description", "updated_at"]
    search_fields = ["key", "description"]
