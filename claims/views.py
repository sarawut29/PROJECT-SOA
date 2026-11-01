from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from .models import BenefitCategory, ClaimRequest, WalletTransaction
from .serializers import (
    BenefitCategorySerializer,
    ClaimRequestSerializer,
    ClaimSubmitSerializer,
    WalletTransactionSerializer
)
from .services import ClaimProcessingService


class BenefitCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BenefitCategory.objects.filter(is_active=True).order_by('id')
    serializer_class = BenefitCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['group', 'requires_insurance_check']
    search_fields = ['name', 'code']


class ClaimRequestViewSet(viewsets.ModelViewSet):
    """
    API จัดการใบคำขอเบิกสวัสดิการ:
    - พนักงานทั่วไป: ดูได้เฉพาะใบเคลมของตนเอง
    - HR Admin: ดูใบเคลมของพนักงานทุกคนได้
    """
    serializer_class = ClaimRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # ป้องกัน drf-yasg Swagger Crash ขณะ Generate Schema
        if getattr(self, 'swagger_fake_view', False):
            return ClaimRequest.objects.none()

        user = self.request.user
        if not user.is_authenticated:
            return ClaimRequest.objects.none()

        if user.role == 'HR_ADMIN':
            return ClaimRequest.objects.all().order_by('-created_at')
        return ClaimRequest.objects.filter(user=user).order_by('-created_at')

    @swagger_auto_schema(
        operation_description="สร้างคำขอเบิกสวัสดิการ (RESTful Standard POST /api/claims/)",
        request_body=ClaimSubmitSerializer,
        responses={201: ClaimRequestSerializer()}
    )
    def create(self, request, *args, **kwargs):
        """รองรับมาตรฐาน RESTful POST /api/claims/ ให้ทำงานผ่าน ClaimProcessingService"""
        return self.submit_claim(request)

    @swagger_auto_schema(
        operation_description="ยกเลิกคำขอเบิกสวัสดิการ (เฉพาะสถานะ PENDING เท่านั้น)",
        responses={200: openapi.Response(description="ยกเลิกคำขอสำเร็จ")}
    )
    def destroy(self, request, *args, **kwargs):
        """รองรับมาตรฐาน RESTful DELETE /api/claims/<id>/ สำหรับยกเลิกคำขอสถานะ PENDING"""
        claim = self.get_object()
        if claim.status != 'PENDING':
            return Response(
                {"message": f"ไม่สามารถยกเลิกคำขอที่อยู่ในสถานะ {claim.status} ได้"},
                status=status.HTTP_400_BAD_REQUEST
            )
        claim_id = claim.id
        claim.delete()
        return Response({"message": f"ยกเลิกคำขอ #{claim_id} สำเร็จแล้ว"}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="ยื่นขอเบิกสวัสดิการ (สถานะเริ่มต้นเป็น PENDING เพื่อรอ HR ตรวจสอบ)",
        request_body=ClaimSubmitSerializer,
        responses={201: ClaimRequestSerializer()}
    )
    @action(detail=False, methods=['post'], url_path='submit')
    def submit_claim(self, request):
        serializer = ClaimSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        category = BenefitCategory.objects.get(id=data['category_id'])

        # สร้างใบคำขอสถานะ PENDING
        claim, is_success, message = ClaimProcessingService.submit_claim(
            user=request.user,
            category=category,
            title=data['title'],
            receipt_number=data['receipt_number'],
            receipt_amount=data['receipt_amount'],
            medical_code=data.get('medical_code', '')
        )

        if not is_success:
            return Response({"message": message}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = ClaimRequestSerializer(claim)
        return Response({
            "message": message,
            "claim": response_serializer.data,
            "current_balance": request.user.flex_point_balance
        }, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(operation_description="เฉพาะ HR Admin: อนุมัติใบคำขอและทำการตัดแต้มสวัสดิการ")
    @action(detail=True, methods=['post'], url_path='approve')
    def approve_claim(self, request, pk=None):
        if request.user.role != 'HR_ADMIN':
            return Response({"detail": "เฉพาะฝ่ายบุคคล (HR Admin) เท่านั้นที่สามารถอนุมัติได้"}, status=status.HTTP_403_FORBIDDEN)

        claim = self.get_object()
        claim, is_success, message = ClaimProcessingService.approve_claim(claim, request.user)
        
        response_serializer = ClaimRequestSerializer(claim)
        http_status = status.HTTP_200_OK if is_success else status.HTTP_400_BAD_REQUEST
        return Response({"message": message, "claim": response_serializer.data}, status=http_status)

    @swagger_auto_schema(operation_description="เฉพาะ HR Admin: ปฏิเสธใบคำขอเบิกสวัสดิการ")
    @action(detail=True, methods=['post'], url_path='reject')
    def reject_claim(self, request, pk=None):
        if request.user.role != 'HR_ADMIN':
            return Response({"detail": "เฉพาะฝ่ายบุคคล (HR Admin) เท่านั้นที่สามารถปฏิเสธได้"}, status=status.HTTP_403_FORBIDDEN)

        reason = request.data.get('reason', 'ข้อมูลหรือเอกสารไม่ถูกต้องตามเงื่อนไข')
        claim = self.get_object()
        claim, is_success, message = ClaimProcessingService.reject_claim(claim, request.user, reason)

        response_serializer = ClaimRequestSerializer(claim)
        http_status = status.HTTP_200_OK if is_success else status.HTTP_400_BAD_REQUEST
        return Response({"message": message, "claim": response_serializer.data}, status=http_status)

    @action(detail=False, methods=['get'], url_path='my-claims')
    def my_claims(self, request):
        """ดูเฉพาะประวัติการเคลมของตนเอง (สำหรับพนักงานและ HR ที่ยื่นสวัสดิการของตนเอง)"""
        claims = ClaimRequest.objects.filter(user=request.user).order_by('-created_at')
        serializer = self.get_serializer(claims, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='pending')
    def pending_claims(self, request):
        """เฉพาะ HR Admin: ดูรายการคำขอทั้งหมดที่กำลังรอการอนุมัติ"""
        if request.user.role != 'HR_ADMIN':
            return Response({"detail": "เฉพาะฝ่ายบุคคล (HR Admin) เท่านั้น"}, status=status.HTTP_403_FORBIDDEN)

        claims = ClaimRequest.objects.filter(status='PENDING').order_by('-created_at')
        serializer = self.get_serializer(claims, many=True)
        return Response(serializer.data)


class WalletTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API สำหรับดูประวัติการเคลื่อนไหวของแต้มในกระเป๋า (Deduct, Refund, Top-up)
    """
    serializer_class = WalletTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return WalletTransaction.objects.none()
        user = self.request.user
        if not user.is_authenticated:
            return WalletTransaction.objects.none()
        return WalletTransaction.objects.filter(user=user).order_by('-created_at')

    @action(detail=False, methods=['get'], url_path='my-balance')
    def my_balance(self, request):
        """ดูแต้มสวัสดิการคงเหลือปัจจุบัน"""
        return Response({
            "username": request.user.username,
            "flex_point_balance": request.user.flex_point_balance,
            "policy_number": request.user.policy_number
        })
