from django.db import models
from dvadmin.utils.models import CoreModel # 继承框架自带的核心模型(包含创建人/时间/备注等)

class SensorDevice(CoreModel):
    """
    传感器设备台账表
    用于 OA 管理设备位置和状态
    """
    did = models.CharField(max_length=50, unique=True, verbose_name="设备标识符(DID)", help_text="如: MSD-99999996")
    name = models.CharField(max_length=100, verbose_name="设备名称", help_text="如: 财务室监测仪")
    location = models.CharField(max_length=100, verbose_name="安装位置", null=True, blank=True)
    status = models.BooleanField(default=True, verbose_name="启用状态")
    location_photo = models.ImageField(
        upload_to='sensor_photos/',  # 只需要写文件夹名称
        verbose_name="位置实景图",
        null=True, 
        blank=True,
        help_text="请上传设备安装位置的实拍图"
    )


    # 可以扩展报警阈值字段，方便在OA里配置
    alert_pm25 = models.FloatField(default=75.0, verbose_name="PM2.5报警阈值")

    class Meta:
        db_table = "sensor_device"
        verbose_name = "环境监测设备"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.name} ({self.did})"

class SensorLog(CoreModel):
    """
    传感器历史数据表
    根据协议文档完善：包含所有 PM 颗粒物细分、有害气体及设备状态
    """
    # === 基础关联 ===
    # 关联到具体的设备 (对应协议中的 DID/MSD-xxx)
    device = models.ForeignKey(
        SensorDevice, 
        on_delete=models.CASCADE, 
        verbose_name="所属设备", 
        related_name="logs",
        db_index=True # 加上索引，提高查询效率
    )
    
    # === 协议状态字段 ===
    tl = models.IntegerField(verbose_name="剩余订阅时间(TL)", null=True, help_text="-1代表一直订阅")
    rssi = models.FloatField(verbose_name="信号强度(RSSI)", null=True, blank=True, help_text="WIFI或4G信号, >22为正常")

    # === 核心环境数据 (温湿度/气压) ===
    temperature = models.FloatField(verbose_name="温度(℃)", null=True, blank=True)
    humidity = models.FloatField(verbose_name="湿度(%RH)", null=True, blank=True)
    pressure = models.FloatField(verbose_name="气压(Pa)", null=True, blank=True, help_text="差压或绝对压力")

    # === 颗粒物细分数据 (单位：ug/m3) ===
    # 协议包含 PM0.3 到 PM100 的 1分钟移动平均值
    pm03 = models.FloatField(verbose_name="PM0.3(ug/m3)", null=True, blank=True)
    pm05 = models.FloatField(verbose_name="PM0.5(ug/m3)", null=True, blank=True)
    pm1 = models.FloatField(verbose_name="PM1.0(ug/m3)", null=True, blank=True)
    pm25 = models.FloatField(verbose_name="PM2.5(ug/m3)", null=True, blank=True)
    pm4 = models.FloatField(verbose_name="PM4.0(ug/m3)", null=True, blank=True)
    pm10 = models.FloatField(verbose_name="PM10(ug/m3)", null=True, blank=True)
    pm100 = models.FloatField(verbose_name="PM100(ug/m3)", null=True, blank=True)

    # === 气体/挥发物数据 ===
    # 注意单位区分：部分是 ppm，部分是 mg/m3，部分是 ug/m3
    co2 = models.FloatField(verbose_name="Co2(ppm)", null=True, blank=True)
    tvoc = models.FloatField(verbose_name="TVOC(mg/m3)", null=True, blank=True)
    ch2o = models.FloatField(verbose_name="甲醛(mg/m3)", null=True, blank=True)
    co = models.FloatField(verbose_name="一氧化碳 Co(mg/m3)", null=True, blank=True)
    
    o3 = models.FloatField(verbose_name="臭氧 O3(ug/m3)", null=True, blank=True)
    so2 = models.FloatField(verbose_name="二氧化硫 So2(ug/m3)", null=True, blank=True)
    no2 = models.FloatField(verbose_name="二氧化氮 No2(ug/m3)", null=True, blank=True)

    class Meta:
        db_table = "sensor_log"
        verbose_name = "环境监测记录"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']