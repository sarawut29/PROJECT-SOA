from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('EMPLOYEE', 'Employee (พนักงาน)'),
        ('HR_ADMIN', 'HR Admin (ฝ่ายบุคคล)'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='EMPLOYEE')
    department = models.CharField(max_length=100, blank=True, null=True, default='IT')
    policy_number = models.CharField(max_length=50, blank=True, null=True) # เลขกรมธรรม์ประกันกลุ่ม
    flex_point_balance = models.DecimalField(max_digits=10, decimal_places=2, default=10000.00) # แต้มเริ่มต้น 10,000

    def __str__(self):
        return f"{self.username} ({self.get_role_display()}) - Balance: {self.flex_point_balance}"
