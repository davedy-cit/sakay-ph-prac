from django.contrib import admin

from .models import (
    DriverPayout, FareShare, Payment, PaymentMethodLookup, Receipt, Wallet, WalletTxn,
)


@admin.register(PaymentMethodLookup)
class PaymentMethodLookupAdmin(admin.ModelAdmin):
    list_display = ["method_code", "method_name", "is_digital", "gateway_name"]
    list_filter = ["is_digital"]
    search_fields = ["method_code", "method_name"]


class WalletTxnInline(admin.TabularInline):
    model = WalletTxn
    extra = 0
    fields = ["txn_type", "amount", "balance_after", "gateway_ref", "created_at"]
    readonly_fields = ["created_at"]
    can_delete = False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ["passenger", "balance", "currency", "updated_at"]
    search_fields = ["passenger__user__full_name", "passenger__user__phone"]
    autocomplete_fields = ["passenger"]
    inlines = [WalletTxnInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["short_id", "ride", "payer", "method", "amount", "status", "paid_at"]
    list_filter = ["status", "method"]
    search_fields = ["id", "gateway_ref", "payer__user__full_name"]
    autocomplete_fields = ["ride", "payer", "method", "wallet"]
    date_hierarchy = "paid_at"

    @admin.display(description="Payment")
    def short_id(self, obj):
        return str(obj.id)[:8]


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ["receipt_no", "payment", "total_amount", "issued_at"]
    search_fields = ["receipt_no"]
    autocomplete_fields = ["payment"]


@admin.register(FareShare)
class FareShareAdmin(admin.ModelAdmin):
    list_display = ["payment", "passenger", "group", "passenger_count",
                    "share_amount", "is_paid"]
    list_filter = ["is_paid"]
    autocomplete_fields = ["payment", "passenger", "group"]


@admin.register(WalletTxn)
class WalletTxnAdmin(admin.ModelAdmin):
    list_display = ["wallet", "txn_type", "amount", "balance_after",
                    "gateway_ref", "created_at"]
    list_filter = ["txn_type"]
    autocomplete_fields = ["wallet", "payment"]


@admin.register(DriverPayout)
class DriverPayoutAdmin(admin.ModelAdmin):
    list_display = ["driver", "method", "amount", "status", "requested_at", "paid_at"]
    list_filter = ["status", "method"]
    autocomplete_fields = ["driver", "method"]
