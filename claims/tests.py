from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from accounts.models import CustomUser
from .models import BenefitCategory, ClaimRequest, WalletTransaction

class ClaimSystemTests(APITestCase):
    def setUp(self):
        # 1. สร้างผู้ใช้: พนักงาน และ HR Admin
        self.employee = CustomUser.objects.create_user(
            username='emp_user',
            password='password123',
            role='EMPLOYEE',
            flex_point_balance=Decimal('10000.00'),
            policy_number='INS-HEALTH-999'
        )

        self.hr_admin = CustomUser.objects.create_user(
            username='hr_admin',
            password='password123',
            role='HR_ADMIN',
            is_staff=True,
            flex_point_balance=Decimal('10000.00')
        )

        # 2. สร้างหมวดหมู่สวัสดิการ
        self.health_cat = BenefitCategory.objects.create(
            code='CAT_HEALTH',
            name='หมวดหมู่สุขภาพ (Health)',
            group='HEALTH',
            requires_insurance_check=True,
            max_limit_per_claim=Decimal('5000.00'),
            is_active=True
        )

        self.learning_cat = BenefitCategory.objects.create(
            code='CAT_LEARNING',
            name='หมวดหมู่การเรียนรู้ (Learning)',
            group='LEARNING',
            requires_insurance_check=False,
            max_limit_per_claim=Decimal('5000.00'),
            is_active=True
        )

    def test_list_benefit_categories(self):
        """1. ทดสอบเรียกดูรายการหมวดหมู่สวัสดิการ"""
        self.client.force_authenticate(user=self.employee)
        response = self.client.get('/api/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle paginated or plain list
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 2)

    def test_submit_health_claim_insurance_calculation(self):
        """2. ทดสอบยื่นเคลมหมวดสุขภาพ: ประกันกลุ่มจ่าย 70% ส่วนต่างรอหักแต้ม"""
        self.client.force_authenticate(user=self.employee)
        payload = {
            'category_id': self.health_cat.id,
            'title': 'ค่าตรวจสุขภาพประจำปี',
            'receipt_number': 'H-REC-2026-001',
            'receipt_amount': '3000.00',
            'medical_code': 'CHK01'
        }
        response = self.client.post('/api/claims/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        claim_data = response.data['claim']
        # ยอด 3,000 * 70% = 2,100 ประกันจ่าย
        self.assertEqual(float(claim_data['insurance_covered_amount']), 2100.00)
        self.assertEqual(claim_data['status'], 'PENDING')
        
        # ขณะเป็น PENDING แต้มพนักงานต้องยังไม่ถูกหัก
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.flex_point_balance, Decimal('10000.00'))

    def test_submit_general_claim_no_insurance(self):
        """3. ทดสอบยื่นเคลมหมวดทั่วไป (Learning): ประกันไม่จ่าย (0 บาท)"""
        self.client.force_authenticate(user=self.employee)
        payload = {
            'category_id': self.learning_cat.id,
            'title': 'คอร์สเรียน Python SOA',
            'receipt_number': 'L-REC-002',
            'receipt_amount': '2500.00'
        }
        response = self.client.post('/api/claims/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        claim_data = response.data['claim']
        self.assertEqual(float(claim_data['insurance_covered_amount']), 0.00)
        self.assertEqual(claim_data['status'], 'PENDING')

    def test_submit_claim_insufficient_points(self):
        """4. ทดสอบยื่นเคลมเมื่อยอดเกินแต้มคงเหลือ ต้องแจ้งเตือนและไม่อนุมัติ"""
        self.client.force_authenticate(user=self.employee)
        payload = {
            'category_id': self.learning_cat.id,
            'title': 'คอร์สเรียนราคาแพงมาก',
            'receipt_number': 'L-REC-003',
            'receipt_amount': '15000.00' # เกินแต้ม 10,000
        }
        response = self.client.post('/api/claims/', payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('แต้มสวัสดิการไม่เพียงพอ', response.data['message'])

    def test_hr_approve_claim_and_deduct_points(self):
        """5. ทดสอบฝ่ายบุคคล (HR) อนุมัติคำขอ -> หักแต้มจริงและสร้าง Wallet Transaction"""
        # สร้างเคลมสุขภาพ 3000 บาท (ประกันจ่าย 2100, พนักงานจ่าย 900)
        claim = ClaimRequest.objects.create(
            user=self.employee,
            category=self.health_cat,
            title='ค่าทำฟัน',
            receipt_number='DENT-001',
            receipt_amount=Decimal('3000.00'),
            insurance_covered_amount=Decimal('2100.00'),
            points_deducted=Decimal('0.00'),
            status='PENDING'
        )

        # HR กดอนุมัติ
        self.client.force_authenticate(user=self.hr_admin)
        response = self.client.post(f'/api/claims/{claim.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # ตรวจสอบสถานะและแต้ม
        claim.refresh_from_db()
        self.assertEqual(claim.status, 'APPROVED')
        self.assertEqual(claim.points_deducted, Decimal('900.00'))

        self.employee.refresh_from_db()
        self.assertEqual(self.employee.flex_point_balance, Decimal('9100.00'))

        # ตรวจสอบ WalletTransaction
        txn = WalletTransaction.objects.filter(claim=claim).first()
        self.assertIsNotNone(txn)
        self.assertEqual(txn.txn_type, 'DEDUCT')
        self.assertEqual(txn.points, Decimal('900.00'))
        self.assertEqual(txn.balance_after, Decimal('9100.00'))

    def test_employee_cannot_approve_claim(self):
        """6. พนักงานทั่วไปไม่มีสิทธิ์อนุมัติคำขอ (403 Forbidden)"""
        claim = ClaimRequest.objects.create(
            user=self.employee,
            category=self.learning_cat,
            title='หนังสือคู่มือ',
            receipt_number='BK-001',
            receipt_amount=Decimal('500.00'),
            status='PENDING'
        )

        self.client.force_authenticate(user=self.employee)
        response = self.client.post(f'/api/claims/{claim.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_hr_reject_claim(self):
        """7. ฝ่ายบุคคล (HR) ปฏิเสธคำขอ -> ปรับสถานะเป็น REJECTED และไม่หักแต้ม"""
        claim = ClaimRequest.objects.create(
            user=self.employee,
            category=self.learning_cat,
            title='อบรมนอกสถานที่',
            receipt_number='TR-001',
            receipt_amount=Decimal('1000.00'),
            status='PENDING'
        )

        self.client.force_authenticate(user=self.hr_admin)
        response = self.client.post(f'/api/claims/{claim.id}/reject/', {'reason': 'ใบเสร็จไม่ชัดเจน'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        claim.refresh_from_db()
        self.assertEqual(claim.status, 'REJECTED')
        self.assertIn('ใบเสร็จไม่ชัดเจน', claim.remarks)

        # แต้มต้องเท่าเดิม
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.flex_point_balance, Decimal('10000.00'))

    def test_cancel_pending_claim_success(self):
        """8. พนักงานยกเลิกคำขอสถานะ PENDING ของตนเองได้ (DELETE)"""
        claim = ClaimRequest.objects.create(
            user=self.employee,
            category=self.learning_cat,
            title='คำขอที่ต้องการยกเลิก',
            receipt_number='CANCEL-001',
            receipt_amount=Decimal('800.00'),
            status='PENDING'
        )

        self.client.force_authenticate(user=self.employee)
        response = self.client.delete(f'/api/claims/{claim.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(ClaimRequest.objects.filter(id=claim.id).exists())

    def test_cannot_cancel_approved_claim(self):
        """9. ไม่สามารถยกเลิกคำขอที่ผ่านการอนุมัติ (APPROVED) แล้วได้"""
        claim = ClaimRequest.objects.create(
            user=self.employee,
            category=self.learning_cat,
            title='คำขอที่อนุมัติแล้ว',
            receipt_number='APPR-001',
            receipt_amount=Decimal('800.00'),
            status='APPROVED'
        )

        self.client.force_authenticate(user=self.employee)
        response = self.client.delete(f'/api/claims/{claim.id}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(ClaimRequest.objects.filter(id=claim.id).exists())
