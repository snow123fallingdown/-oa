import base64
import hashlib
from datetime import datetime, timedelta
from captcha.views import CaptchaStore, captcha_image
from django.contrib import auth
from django.contrib.auth import login
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Q
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from django.conf import settings
from application import dispatch
from dvadmin.system.models import Users
from dvadmin.utils.json_response import ErrorResponse, DetailResponse
from dvadmin.utils.request_util import save_login_log
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.validator import CustomValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from dvadmin.utils.json_response import SuccessResponse, ErrorResponse

class CaptchaView(APIView):
    authentication_classes = []
    permission_classes = []

    @swagger_auto_schema(
        responses={"200": openapi.Response("获取成功")},
        security=[],
        operation_id="captcha-get",
        operation_description="验证码获取",
    )
    def get(self, request):
        data = {}
        # 注意：这里获取验证码的接口如果你想保留功能，可以不用改，
        # 但登录校验那里我已经强制关闭了。
        if dispatch.get_system_config_values("base.captcha_state"):
            hashkey = CaptchaStore.generate_key()
            id = CaptchaStore.objects.filter(hashkey=hashkey).first().id
            imgage = captcha_image(request, hashkey)
            # 将图片转换为base64
            image_base = base64.b64encode(imgage.content)
            data = {
                "key": id,
                "image_base": "data:image/png;base64," + image_base.decode("utf-8"),
            }
        return DetailResponse(data=data)


class LoginSerializer(TokenObtainPairSerializer):
    """
    登录的序列化器:
    重写djangorestframework-simplejwt的序列化器
    """
    captcha = serializers.CharField(
        max_length=6, required=False, allow_null=True, allow_blank=True
    )

    class Meta:
        model = Users
        fields = "__all__"
        read_only_fields = ["id"]

    default_error_messages = {"no_active_account": _("账号/密码错误")}

    def validate(self, attrs):
        # 打印日志，用于确认你运行的是这份代码
        print(">>> 正在执行【免验证码】登录逻辑 <<<")

        captcha = self.initial_data.get("captcha", None)
        
        # =================================================================
        # 【修改关键点】强制设置为 False，直接跳过验证码校验
        # 原代码：if dispatch.get_system_config_values("base.captcha_state"):
        # =================================================================
        if False: 
            if captcha is None:
                raise CustomValidationError("验证码不能为空")
            self.image_code = CaptchaStore.objects.filter(
                id=self.initial_data["captchaKey"]
            ).first()
            five_minute_ago = datetime.now() - timedelta(hours=0, minutes=5, seconds=0)
            if self.image_code and five_minute_ago > self.image_code.expiration:
                self.image_code and self.image_code.delete()
                raise CustomValidationError("验证码过期")
            else:
                if self.image_code and (
                    self.image_code.response == captcha
                    or self.image_code.challenge == captcha
                ):
                    self.image_code and self.image_code.delete()
                else:
                    self.image_code and self.image_code.delete()
                    raise CustomValidationError("图片验证码错误")
        
        # --- 下面是账号密码校验逻辑 ---
        try:
            user = Users.objects.get(
                Q(username=attrs['username']) | Q(email=attrs['username']) | Q(mobile=attrs['username']))
        except Users.DoesNotExist:
            raise CustomValidationError("您登录的账号不存在")
        except Users.MultipleObjectsReturned:
            raise CustomValidationError("您登录的账号存在多个,请联系管理员检查登录账号唯一性")
        # 验证密码
        from django.contrib.auth.hashers import check_password
        import hashlib
        password = attrs.get('password')
        verify = check_password(password, user.password)
        if not verify:
            md5_pwd = hashlib.md5(password.encode(encoding='UTF-8')).hexdigest()
            verify = check_password(md5_pwd, user.password)
        if not verify:
            raise CustomValidationError("账号/密码错误")
        
        # 直接生成token，不走父类验证（避免is_active检查）
        refresh = RefreshToken.for_user(user)
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        data["username"] = user.username
        data["name"] = user.name
        data["userId"] = user.id
        data["avatar"] = str(user.avatar) if user.avatar else ""
        data['user_type'] = user.user_type
        data['pwd_change_count'] = user.pwd_change_count
        dept = getattr(user, 'dept', None)
        if dept:
            data['dept_info'] = {
                'dept_id': dept.id,
                'dept_name': dept.name,
            }
        role = getattr(user, 'role', None)
        if role:
            data['role_info'] = role.values('id', 'name', 'key')
        request = self.context.get("request")
        request.user = user
        # 记录登录日志
        save_login_log(request=request)
        return {"code": 2000, "msg": "请求成功", "data": data}


class LoginView(TokenObtainPairView):
    """
    登录接口
    """
    serializer_class = LoginSerializer
    permission_classes = []
    # post 方法保持注释，让它直接使用 serializer_class 处理
    

class LoginTokenSerializer(TokenObtainPairSerializer):
    """
    登录的序列化器:
    """

    class Meta:
        model = Users
        fields = "__all__"
        read_only_fields = ["id"]

    default_error_messages = {"no_active_account": _("账号/密码不正确")}

    def validate(self, attrs):
        if not getattr(settings, "LOGIN_NO_CAPTCHA_AUTH", False):
            return {"code": 4000, "msg": "该接口暂未开通!", "data": None}
        data = super().validate(attrs)
        data["name"] = self.user.name
        data["userId"] = self.user.id
        return {"code": 2000, "msg": "请求成功", "data": data}


class LoginTokenView(TokenObtainPairView):
    """
    登录获取token接口
    """

    serializer_class = LoginTokenSerializer
    permission_classes = []


class LogoutView(APIView):
    def post(self, request):
        return DetailResponse(msg="注销成功")


class ApiLoginSerializer(CustomModelSerializer):
    """接口文档登录-序列化器"""

    username = serializers.CharField()
    password = serializers.CharField()

    class Meta:
        model = Users
        fields = ["username", "password"]


class ApiLogin(APIView):
    """接口文档的登录接口"""

    serializer_class = ApiLoginSerializer
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user_obj = auth.authenticate(
            request,
            username=username,
            password=hashlib.md5(password.encode(encoding="UTF-8")).hexdigest(),
        )
        if user_obj:
            login(request, user_obj)
            return redirect("/")
        else:
            return ErrorResponse(msg="账号/密码错误")
        
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return SuccessResponse(msg="退出成功")