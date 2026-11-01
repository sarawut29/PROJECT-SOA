from rest_framework import generics, permissions
from rest_framework.response import Response
from .models import CustomUser
from .serializers import RegisterSerializer, UserProfileSerializer

class RegisterView(generics.CreateAPIView):
    """
    API สำหรับพนักงานสมัครสมาชิกใหม่ (ได้รับแต้มตั้งต้น 10,000 แต้ม)
    """
    queryset = CustomUser.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    API สำหรับดูข้อมูลส่วนตัวและแต้มคงเหลือ (ต้องแนบ JWT Token)
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # คืนค่าผู้ใช้ปัจจุบันที่ส่ง Token เข้ามา
        return self.request.user
