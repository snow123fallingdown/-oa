import hashlib
import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password
from django.utils import timezone

from dvadmin.utils.validator import CustomValidationError

logger = logging.getLogger(__name__)
UserModel = get_user_model()


class CustomBackend(ModelBackend):
    """
    Django原生认证方式
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        msg = '%s 正在使用本地登录...' % username
        logger.info(msg)
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        try:
            user = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            UserModel().set_password(password)
        else:
            verify_password = check_password(password, user.password)
            if not verify_password:
                md5_pwd = hashlib.md5(password.encode(encoding='UTF-8')).hexdigest()
                verify_password = check_password(md5_pwd, user.password)
            if verify_password:
                user.last_login = timezone.now()
                user.save()
                return user
            else:
                raise CustomValidationError("账号/密码错误")
