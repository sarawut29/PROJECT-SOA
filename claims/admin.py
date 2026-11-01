from django.contrib import admin
from .models import BenefitCategory, ClaimRequest, WalletTransaction

@admin.register(BenefitCategory)
class BenefitCategoryAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'group', 'requires_insurance_check', 'max_limit_per_claim', 'is_active']
    list_filter = ['group', 'requires_insurance_check', 'is_active']
    search_fields = ['code', 'name']

@admin.register(ClaimRequest)
class ClaimRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'category', 'receipt_amount', 'insurance_covered_amount', 'points_deducted', 'status', 'created_at']
    list_filter = ['status', 'category__group']
    search_fields = ['user__username', 'title', 'medical_code']

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'txn_type', 'points', 'balance_after', 'created_at']
    list_filter = ['txn_type']
