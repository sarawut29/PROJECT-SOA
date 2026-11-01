from rest_framework import serializers
from .models import BenefitCategory, ClaimRequest, WalletTransaction
from decimal import Decimal

class BenefitCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BenefitCategory
        fields = '__all__'


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = ['id', 'claim', 'points', 'balance_after', 'txn_type', 'description', 'created_at']


class ClaimRequestSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_group = serializers.CharField(source='category.get_group_display', read_only=True)
    class Meta:
        model = ClaimRequest
        fields = [
            'id', 'user', 'user_name', 'category', 'category_name', 'category_group',
            'title', 'receipt_number', 'receipt_amount', 'medical_code',
            'insurance_covered_amount', 'points_deducted',
            'status', 'remarks', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'insurance_covered_amount', 'points_deducted', 'status', 'remarks', 'created_at', 'updated_at']
class ClaimSubmitSerializer(serializers.Serializer):
    category_id = serializers.IntegerField(required=True)
    title = serializers.CharField(max_length=200, required=True)
    receipt_number = serializers.CharField(max_length=100, required=True) # เลขที่ใบเสร็จ
    receipt_amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('1.00'), required=True)
    medical_code = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    def validate_category_id(self, value):
        if not BenefitCategory.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("ไม่พบหมวดหมู่สวัสดิการนี้")
        return value
