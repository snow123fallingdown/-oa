# -*- coding: utf-8 -*-
"""
自定义JWT认证 - 不检查is_active
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed


class CustomJWTAuthentication(JWTAuthentication):
    """
    自定义JWT认证 - 不检查用户is_active状态
    """
    
    def get_user(self, validated_token):
        """
        重写get_user，移除is_active检查
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user_id = validated_token['user_id']
        except KeyError:
            raise AuthenticationFailed('Token contained no recognizable user identification')

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found', code='user_not_found')

        # 原代码会检查: if not user.is_active: raise AuthenticationFailed(...)
        # 我们这里跳过is_active检查，只返回用户
        return user
