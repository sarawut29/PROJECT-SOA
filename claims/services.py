from decimal import Decimal
from django.db import transaction
from .models import ClaimRequest, WalletTransaction

class ClaimProcessingService:
    """
    Service Layer ทำหน้าที่ Service Orchestration:
    1. ตรวจสอบสิทธิ์ประกันสุขภาพกลุ่ม (ถ้าเป็นหมวด Health)
    2. คำนวณยอดที่ประกันจ่าย (Coverage) และยอดส่วนต่าง (Copay)
    3. สร้างใบคำขอสถานะ PENDING เพื่อรอฝ่ายบุคคล (HR) ตรวจสอบ
    4. เมื่อ HR อนุมัติ -> ตรวจสอบแต้มและทำการหักแต้มในกระเป๋า Flex Points
    """

    @staticmethod
    def calculate_insurance_coverage(category, receipt_amount, policy_number):
        """
        จำลองการเรียก Corporate Insurance Gateway Service:
        - หมวดหมู่สุขภาพ (Health): ประกันกลุ่มคุ้มครอง 70% ของใบเสร็จ (ไม่เกินวงเงินสูงสุดของหมวด)
        - หมวดหมู่อื่นๆ (Travel, Learning, Lifestyle, IT): ประกันจ่าย 0 บาท
        """
        receipt_amount = Decimal(str(receipt_amount))
        
        if not category.requires_insurance_check:
            return Decimal('0.00')

        coverage_rate = Decimal('0.70')
        covered = receipt_amount * coverage_rate
        max_limit = category.max_limit_per_claim
        
        return min(covered, max_limit).quantize(Decimal('0.01'))

    @classmethod
    def submit_claim(cls, user, category, title, receipt_number, receipt_amount, medical_code=None):
        """
        พนักงานกดยื่นเคลม -> สร้างใบคำขอสถานะ PENDING (ยังไม่ตัดแต้ม)
        """
        receipt_amount = Decimal(str(receipt_amount))
        insurance_covered = cls.calculate_insurance_coverage(category, receipt_amount, user.policy_number)
        copay_remaining = receipt_amount - insurance_covered

        # ตรวจสอบเบื้องต้นว่าแต้มพอหรือไม่ ถ้าแต้มไม่พอเตือนตั้งแต่ตอนยื่น
        if user.flex_point_balance < copay_remaining:
            return None, False, f"แต้มสวัสดิการไม่เพียงพอ (ต้องการ {copay_remaining} แต้ม แต่มีคงเหลือ {user.flex_point_balance} แต้ม)"

        claim = ClaimRequest.objects.create(
            user=user,
            category=category,
            title=title,
            receipt_number=receipt_number,
            receipt_amount=receipt_amount,
            medical_code=medical_code,
            insurance_covered_amount=insurance_covered,
            points_deducted=Decimal('0.00'), # ยังไม่หักแต้มจนกว่า HR จะอนุมัติ
            status='PENDING',
            remarks="รอฝ่ายบุคคล (HR) ตรวจสอบเอกสารและอนุมัติ"
        )

        return claim, True, "ยื่นคำขอสำเร็จแล้ว สถานะ: รอการอนุมัติ (PENDING)"

    @classmethod
    def approve_claim(cls, claim, hr_user):
        """
        HR กดอนุมัติคำขอ -> ทำการหักแต้มจากกระเป๋าพนักงานจริง
        """
        if claim.status != 'PENDING':
            return claim, False, f"ใบคำขอนี้ไม่อยู่ในสถานะรออนุมัติ (สถานะปัจจุบัน: {claim.status})"

        user = claim.user
        copay_remaining = claim.receipt_amount - claim.insurance_covered_amount

        # ตรวจสอบแต้มคงเหลือของพนักงานอีกครั้ง ณ เวลาอนุมัติ
        if user.flex_point_balance < copay_remaining:
            claim.status = 'REJECTED'
            claim.remarks = f"ปฏิเสธโดย HR ({hr_user.username}): แต้มคงเหลือไม่เพียงพอในขณะอนุมัติ"
            claim.save()
            return claim, False, "ไม่สามารถอนุมัติได้ เนื่องจากแต้มสวัสดิการของพนักงานไม่เพียงพอ"

        with transaction.atomic():
            # 1. หักแต้มจากกระเป๋าพนักงาน
            user.flex_point_balance -= copay_remaining
            user.save()

            # 2. ปรับสถานะใบเคลมเป็น APPROVED
            claim.status = 'APPROVED'
            claim.points_deducted = copay_remaining
            claim.remarks = f"อนุมัติโดย HR ({hr_user.username}): ประกันจ่าย {claim.insurance_covered_amount} บ., หักแต้ม {copay_remaining} แต้ม"
            claim.save()

            # 3. บันทึก Transaction ประวัติการตัดแต้ม
            WalletTransaction.objects.create(
                user=user,
                claim=claim,
                points=copay_remaining,
                balance_after=user.flex_point_balance,
                txn_type='DEDUCT',
                description=f"หักสวัสดิการ: {claim.title} (ใบคำขอ #{claim.id})"
            )

        return claim, True, f"อนุมัติใบคำขอ #{claim.id} และหักแต้มสวัสดิการเรียบร้อยแล้ว"

    @classmethod
    def reject_claim(cls, claim, hr_user, reason="เอกสารหรือข้อมูลไม่ครบถ้วน"):
        """
        HR ปฏิเสธคำขอ
        """
        if claim.status != 'PENDING':
            return claim, False, f"ใบคำขอนี้ไม่อยู่ในสถานะรออนุมัติ (สถานะปัจจุบัน: {claim.status})"

        claim.status = 'REJECTED'
        claim.remarks = f"ปฏิเสธโดย HR ({hr_user.username}): {reason}"
        claim.save()

        return claim, True, f"ปฏิเสธใบคำขอ #{claim.id} เรียบร้อยแล้ว"

