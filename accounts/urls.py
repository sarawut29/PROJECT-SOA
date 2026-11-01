from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import RegisterView, UserProfileView

urlpatterns = [
    # 1. สมัครสมาชิก
    path('register/', RegisterView.as_view(), name='auth_register'),
    
    # 2. เข้าสู่ระบบ รับ JWT Access Token & Refresh Token (Lab 8)
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    
    # 3. ขอ Refresh Token ใหม่เมื่อ Access Token หมดอายุ
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # 4. ดูข้อมูลส่วนตัวและแต้มคงเหลือ
    path('profile/', UserProfileView.as_view(), name='user_profile'),
]
