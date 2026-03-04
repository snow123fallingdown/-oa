from rest_framework.response import Response
from dvadmin.utils.viewset import CustomModelViewSet
from .models import SensorDevice, SensorLog
from dvadmin.utils.json_response import DetailResponse
from .serializers import SensorDeviceSerializer, SensorLogSerializer
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated


class SensorDeviceViewSet(CustomModelViewSet):
    queryset = SensorDevice.objects.all()
    serializer_class = SensorDeviceSerializer
    search_fields = "__all__"
    lookup_field = 'did' 
    
    def update(self, request, *args, **kwargs):
        """
        特洛伊木马战术：
        拦截 PUT 请求，强行开启 'partial=True' (局部更新模式)。
        这样前端发 PUT 请求时，只传一个字段也不会报错。
        """
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)



    # ================= 核心修改开始 =================
    @action(methods=['GET'], detail=True, permission_classes=[IsAuthenticated])
    def latest_data(self, request, *args, **kwargs):
        """
        获取指定设备的最新一条监测数据
        """
        # 1. 获取当前请求的设备对象
        # self.get_object() 会自动从 kwargs 里读取 did 参数去数据库查询
        device = self.get_object()
        
        # 2. 查询关联日志
        latest_log = device.logs.first()

        if latest_log:
            serializer = SensorLogSerializer(latest_log)
            return DetailResponse(data=serializer.data, msg="获取最新数据成功")
        else:
            return DetailResponse(data=None, msg="该设备暂无监测记录")
        
    @action(methods=['POST'], detail=True, url_path='upload')
    def upload_photo(self, request, *args, **kwargs):
        # 1. 获取当前操作的设备对象 (DRF 会自动根据 did 查找)
        obj = self.get_object() 
        
        # 2. 获取上传的文件
        file_obj = request.data.get('location_photo')
        if not file_obj:
             return Response({"code": 4000, "msg": "未检测到上传的文件", "data": None})

        # 3. 手动保存图片
        obj.location_photo = file_obj
        obj.save()

        # 4. 返回最新数据
        serializer = self.get_serializer(obj)
        return Response({
            "code": 2000,
            "msg": "图片上传成功",
            "data": serializer.data
        })

class SensorLogViewSet(CustomModelViewSet):
    queryset = SensorLog.objects.all()
    serializer_class = SensorLogSerializer
    filter_fields = ['device', 'device__did'] # 支持按设备筛选
    ordering_fields =  "__all__"


