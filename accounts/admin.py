from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'role', 'department', 'flex_point_balance', 'policy_number', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('ข้อมูลสวัสดิการและองค์กร', {'fields': ('role', 'department', 'policy_number', 'flex_point_balance')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)
