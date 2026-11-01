from django.db import models
from django.conf import settings

class BenefitCategory(models.Model):
    GROUP_CHOICES = [
        ('HEALTH', 'สุขภาพและสิ่งจำยอม (Health & Wellness)'),
        ('TRAVEL', 'การเดินทางและปฏิบัติงาน (Travel & Operations)'),
        ('LEARNING', 'การพัฒนาตนเอง (Learning & Development)'),
        ('LIFESTYLE', 'ไลฟ์สไตล์และความเป็นอยู่ (Flexible Benefits)'),
        ('EQUIPMENT', 'อุปกรณ์และเทคโนโลยี (Equipment & Technology)'),
    ]

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=150)
    group = models.CharField(max_length=20, choices=GROUP_CHOICES)
    description = models.TextField(blank=True)
    requires_insurance_check = models.BooleanField(default=False)
    max_limit_per_claim = models.DecimalField(max_digits=10, decimal_places=2, default=5000.00)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"[{self.code}] {self.name}"


class ClaimRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'รอการอนุมัติ (Pending)'),
        ('APPROVED', 'อนุมัติแล้ว (Approved)'),
        ('REJECTED', 'ปฏิเสธ (Rejected)'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='claims')
    category = models.ForeignKey(BenefitCategory, on_delete=models.PROTECT, related_name='claims')
    title = models.CharField(max_length=200)
    receipt_amount = models.DecimalField(max_digits=10, decimal_places=2) # ยอดตามใบเสร็จ
    receipt_number = models.CharField(max_length=100, blank=True, default='') # เลขที่ใบเสร็จ/ใบกำกับภาษี
    medical_code = models.CharField(max_length=50, blank=True, null=True) # รหัสโรค/การรักษา (ถ้ามี)
    
    # ยอดคำนวณจากระบบ
    insurance_covered_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # ประกันช่วยจ่าย
    points_deducted = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # แต้มที่ตัดจากกระเป๋าจริง
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    remarks = models.TextField(blank=True, null=True) # หมายเหตุ/เหตุผลกรณีปฏิเสธ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Claim #{self.id} - {self.user.username} ({self.status})"


class WalletTransaction(models.Model):
    TXN_TYPE_CHOICES = [
        ('DEDUCT', 'หักแต้มสวัสดิการ (Deduct)'),
        ('REFUND', 'คืนแต้มสวัสดิการ (Refund)'),
        ('TOPUP', 'เติมแต้มประจำปี (Top-up)'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet_transactions')
    claim = models.ForeignKey(ClaimRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    points = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    txn_type = models.CharField(max_length=20, choices=TXN_TYPE_CHOICES, default='DEDUCT')
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Txn #{self.id} - {self.user.username} ({self.txn_type} {self.points})"
