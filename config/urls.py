"""
URL configuration for config project.
"""
import os
from pathlib import Path
from django.contrib import admin
from django.urls import path, include
from django.http import FileResponse, Http404
from django.conf import settings
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# ตั้งค่าเอกสาร Swagger API (Lab 9)
schema_view = get_schema_view(
    openapi.Info(
        title="Flexible Benefit & Health Claim SOA API",
        default_version='v1',
        description="ระบบจัดการสวัสดิการยืดหยุ่นและเคลมประกันสุขภาพภายในองค์กร",
        contact=openapi.Contact(email="admin@company.com"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

def serve_frontend_index(request):
    index_file = os.path.join(settings.BASE_DIR, 'frontend', 'index.html')
    if os.path.exists(index_file):
        return FileResponse(open(index_file, 'rb'), content_type='text/html')
    raise Http404("Frontend index not found")

def serve_frontend_asset(request, filename):
    file_path = os.path.join(settings.BASE_DIR, 'frontend', filename)
    if os.path.exists(file_path):
        content_type = 'text/css' if filename.endswith('.css') else 'application/javascript'
        return FileResponse(open(file_path, 'rb'), content_type=content_type)
    raise Http404(f"Asset {filename} not found")

urlpatterns = [
    # หน้าหลัก Web Portal
    path('', serve_frontend_index, name='frontend_home'),
    path('style.css', lambda r: serve_frontend_asset(r, 'style.css'), name='frontend_style'),
    path('app.js', lambda r: serve_frontend_asset(r, 'app.js'), name='frontend_script'),

    # Django Admin
    path('admin/', admin.site.urls),
    
    # Swagger & ReDoc API Documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # API Endpoints
    path('api/auth/', include('accounts.urls')),
    path('api/', include('claims.urls')),
]
