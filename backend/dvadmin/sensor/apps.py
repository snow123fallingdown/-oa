from django.apps import AppConfig


class SensorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # 原来可能是 name = 'sensor'
    # 必须改为全路径，加上前缀 dvadmin
    name = 'dvadmin.sensor' 
    verbose_name = "环境监测管理" # 在后台显示的中文名称