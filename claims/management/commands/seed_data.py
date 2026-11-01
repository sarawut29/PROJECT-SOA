from decimal import Decimal
from django.core.management.base import BaseCommand
from accounts.models import CustomUser
from claims.models import BenefitCategory

class Command(BaseCommand):
    help = 'สร้างข้อมูลตั้งต้นสำหรับระบบสวัสดิการ (Categories และ Demo Users)'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding default categories...")
        categories = [
            {
                'code': 'CAT_HEALTH',
                'name': '1. หมวดหมู่สุขภาพ (Health & Wellness)',
                'group': 'HEALTH',
                'description': 'ค่ารักษาพยาบาล ทันตกรรม ตรวจสุขภาพ (ประกันกลุ่มจ่าย 70%)',
                'requires_insurance_check': True,
                'max_limit_per_claim': Decimal('5000.00'),
                'is_active': True,
            },
            {
                'code': 'CAT_TRAVEL',
                'name': '2. หมวดหมู่การเดินทางและปฏิบัติงาน (Travel & Operations)',
                'group': 'TRAVEL',
                'description': 'ค่าเดินทาง เบี้ยเลี้ยง ปฏิบัติงานนอกสถานที่',
                'requires_insurance_check': False,
                'max_limit_per_claim': Decimal('3000.00'),
                'is_active': True,
            },
            {
                'code': 'CAT_LEARNING',
                'name': '3. หมวดหมู่การพัฒนาตนเอง (Learning & Development)',
                'group': 'LEARNING',
                'description': 'คอร์สเรียน หนังสือ ค่าอบรม สอบใบรับรอง Certificate',
                'requires_insurance_check': False,
                'max_limit_per_claim': Decimal('5000.00'),
                'is_active': True,
            },
            {
                'code': 'CAT_EQUIPMENT',
                'name': '4. หมวดหมู่อุปกรณ์และเทคโนโลยี (Equipment & IT)',
                'group': 'EQUIPMENT',
                'description': 'อุปกรณ์ทำงาน เมาส์ คีย์บอร์ด อุปกรณ์ IT Ergonomics',
                'requires_insurance_check': False,
                'max_limit_per_claim': Decimal('5000.00'),
                'is_active': True,
            },
        ]

        for cat_data in categories:
            cat, created = BenefitCategory.objects.get_or_create(
                code=cat_data['code'],
                defaults=cat_data
            )
            status_text = "Created" if created else "Exists"
            self.stdout.write(f"- Category [{cat.code}]: {status_text}")

        self.stdout.write("Seeding demo users...")
        if not CustomUser.objects.filter(username='67310124').exists():
            u = CustomUser.objects.create_user(
                username='67310124',
                password='password123',
                email='admin@company.com',
                first_name='Admin',
                last_name='HR',
                role='HR_ADMIN',
                is_staff=True,
                is_superuser=True,
                flex_point_balance=Decimal('100000.00'),
                policy_number='INS-GROUP-2026'
            )
            self.stdout.write(f"- User [{u.username}]: Created (HR Admin)")
        else:
            self.stdout.write("- User [67310124]: Exists")

        if not CustomUser.objects.filter(username='emp01').exists():
            u2 = CustomUser.objects.create_user(
                username='emp01',
                password='password123',
                email='emp01@company.com',
                first_name='Somchai',
                last_name='Jaidee',
                role='EMPLOYEE',
                flex_point_balance=Decimal('10000.00'),
                policy_number='INS-EMP-001'
            )
            self.stdout.write(f"- User [{u2.username}]: Created (Employee)")
        else:
            self.stdout.write("- User [emp01]: Exists")

        self.stdout.write(self.style.SUCCESS("Successfully seeded all data!"))
