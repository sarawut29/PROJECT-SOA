from rest_framework import serializers
from .models import CustomUser

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, min_length=6, style={'input_type': 'password'})

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'confirm_password', 'first_name', 'last_name', 'department', 'policy_number']

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "รหัสผ่านทั้งสองช่องไม่ตรงกัน"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = CustomUser(**validated_data)
        user.set_password(password) # แฮชรหัสผ่านให้ปลอดภัย
        user.role = 'EMPLOYEE'      # ผู้สมัครใหม่เป็น Employee เริ่มต้น
        user.flex_point_balance = 10000.00 # แต้มเริ่มต้น 10,000 แต้ม
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'department', 'policy_number', 'flex_point_balance']
        read_only_fields = ['id', 'username', 'role', 'is_staff', 'flex_point_balance']
