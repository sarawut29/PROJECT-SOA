from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import CustomUser

class AccountsAuthTests(APITestCase):
    def setUp(self):
        self.register_url = reverse('auth_register')
        self.login_url = reverse('token_obtain_pair')
        self.profile_url = reverse('user_profile')

        self.user_data = {
            'username': 'somchai',
            'email': 'somchai@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'first_name': 'Somchai',
            'last_name': 'Dee',
            'department': 'IT',
            'policy_number': 'INS-2026-001'
        }

    def test_user_registration_success(self):
        """1. ทดสอบสมัครสมาชิกพนักงานใหม่ และได้รับแต้มตั้งต้น 10,000 แต้ม"""
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        user = CustomUser.objects.get(username='somchai')
        self.assertEqual(user.role, 'EMPLOYEE')
        self.assertEqual(float(user.flex_point_balance), 10000.00)

    def test_user_registration_password_mismatch(self):
        """2. ทดสอบกรณีรหัสผ่านและยืนยันรหัสผ่านไม่ตรงกัน"""
        bad_data = self.user_data.copy()
        bad_data['confirm_password'] = 'wrongpass'
        response = self.client.post(self.register_url, bad_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_jwt_login_success(self):
        """3. ทดสอบเข้าสู่ระบบและได้รับ JWT Access & Refresh Token"""
        CustomUser.objects.create_user(
            username='somchai',
            password='password123',
            role='EMPLOYEE'
        )
        login_data = {'username': 'somchai', 'password': 'password123'}
        response = self.client.post(self.login_url, login_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_get_user_profile_authenticated(self):
        """4. ทดสอบดูข้อมูล Profile ด้วย Bearer Token"""
        user = CustomUser.objects.create_user(
            username='somchai',
            password='password123',
            role='EMPLOYEE',
            flex_point_balance=10000.00
        )
        self.client.force_authenticate(user=user)
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'somchai')
        self.assertEqual(float(response.data['flex_point_balance']), 10000.00)

    def test_get_user_profile_unauthorized(self):
        """5. ทดสอบดูข้อมูล Profile โดยไม่แนบ Token จะต้องถูกปฏิเสธ 401"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
