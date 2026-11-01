from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BenefitCategoryViewSet, ClaimRequestViewSet, WalletTransactionViewSet

router = DefaultRouter()
router.register(r'categories', BenefitCategoryViewSet, basename='category')
router.register(r'claims', ClaimRequestViewSet, basename='claim')
router.register(r'wallet/transactions', WalletTransactionViewSet, basename='wallet-transaction')

urlpatterns = [
    path('', include(router.urls)),
]
