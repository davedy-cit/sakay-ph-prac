from django.contrib import admin

from .models import SOSAlert, SOSNotification, TrustedContact


@admin.register(TrustedContact)
class TrustedContactAdmin(admin.ModelAdmin):
    list_display = ["contact_name", "passenger", "contact_mobile", "relationship"]
    search_fields = ["contact_name", "contact_mobile", "passenger__user__full_name"]
    autocomplete_fields = ["passenger"]


class SOSNotificationInline(admin.TabularInline):
    model = SOSNotification
    extra = 0
    fields = ["contact", "delivery_status", "notified_at"]
    autocomplete_fields = ["contact"]


@admin.register(SOSAlert)
class SOSAlertAdmin(admin.ModelAdmin):
    list_display = ["short_id", "ride", "raised_by", "alert_type", "status",
                    "triggered_at", "resolved_at"]
    list_filter = ["status", "alert_type"]
    search_fields = ["id", "ride__id", "raised_by__full_name"]
    readonly_fields = ["id", "triggered_at"]
    autocomplete_fields = ["ride", "raised_by"]
    inlines = [SOSNotificationInline]
    date_hierarchy = "triggered_at"

    @admin.display(description="Alert")
    def short_id(self, obj):
        return str(obj.id)[:8]


@admin.register(SOSNotification)
class SOSNotificationAdmin(admin.ModelAdmin):
    list_display = ["alert", "contact", "delivery_status", "notified_at"]
    list_filter = ["delivery_status"]
    autocomplete_fields = ["alert", "contact"]
