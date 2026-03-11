import json
import logging
import threading
import time
from django.core.management.base import BaseCommand
from django.utils import timezone
import paho.mqtt.client as mqtt

# 请确保导入路径与您的项目结构一致
from dvadmin.sensor.models import SensorDevice, SensorLog

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '分布式 MQTT 监听服务（无密码脱敏版）'

    # 协议 Key 到 数据库字段的映射表
    KEY_MAPPING = {
        "T": "temperature", "HUM": "humidity", "Co2": "co2", "TVoc": "tvoc",
        "PM0.3": "pm03", "PM0.5": "pm05", "PM1": "pm1", "PM2.5": "pm25",
        "PM4": "pm4", "PM10": "pm10", "PM100": "pm100", 
        "O3": "o3", "So2": "so2", "No2": "no2", "CH2O": "ch2o",
        "Co": "co", "Pressure": "pressure", "RSSI": "rssi"
    }

    def handle(self, *args, **options):
        # 1. 获取所有已启用的设备
        devices = SensorDevice.objects.filter(status=True)
        
        if not devices.exists():
            self.stdout.write(self.style.WARNING("未发现启用设备。"))
            return

        self.stdout.write(self.style.SUCCESS(f"--- 启动监听服务，共 {devices.count()} 个设备 ---"))

        # 2. 为每个设备启动独立的监听线程
        for device in devices:
            t = threading.Thread(
                target=self.start_mqtt_worker, 
                args=(device,), 
                name=f"Thread-{device.did}"
            )
            t.daemon = True
            t.start()
            # 仅显示名称和识别码，不暴露 IP 和端口
            self.stdout.write(f"  > [ {device.name} ] 监听线程已就绪")

        # 3. 主线程保持运行
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("\n服务已手动停止"))

    def start_mqtt_worker(self, device):
        """
        核心 Worker：直接从对象读取参数，不暴露敏感变量
        """
        # 使用 DID 动态生成唯一的 Client ID
        client_id = f"SINK_{device.did}_{str(int(time.time()))[-4:]}"
        client = mqtt.Client(client_id=client_id)

        # 绑定回调（通过 lambda 传入当前设备对象）
        client.on_connect = lambda c, u, f, rc: self.on_connect(c, u, f, rc, device)
        client.on_message = lambda c, u, m: self.on_message(c, u, m, device)

        while True:
            try:
                # 动态获取连接参数，若字段不存在则使用默认值，确保不崩溃
                client.connect(
                    host=getattr(device, 'broker_ip', '127.0.0.1'), 
                    port=int(getattr(device, 'broker_port', 1883)), 
                    keepalive=60
                )
                client.loop_forever()
            except Exception:
                # 异常不打印具体 IP，仅记录设备名称
                logger.error(f"设备 [{device.name}] 连接异常，15秒后重试...")
                time.sleep(15)

    def on_connect(self, client, userdata, flags, rc, device):
        if rc == 0:
            # 获取订阅主题，默认值为 /device/sensors
            topic = getattr(device, 'subscribe_topic', '/device/sensors')
            client.subscribe(topic)
            self.stdout.write(self.style.SUCCESS(f" [√] {device.name} 已连接"))
        else:
            logger.error(f" [×] {device.name} 连接失败，错误码: {rc}")

    def on_message(self, client, userdata, msg, device):
        """
        解析数据并入库
        """
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            sensors = payload.get("sensor", [])
            
            # 构建入库数据
            db_data = {
                "tl": payload.get("TL"),
                "device": device
            }

            for item in sensors:
                raw_key = str(item.get("2", "")).strip()
                field_name = self.KEY_MAPPING.get(raw_key)
                if field_name:
                    db_data[field_name] = item.get("3")

            # 写入日志表
            SensorLog.objects.create(**db_data)

            # 更新设备最后在线时间
            SensorDevice.objects.filter(pk=device.pk).update(last_online=timezone.now())

            # 仅打印设备名称，不显示具体数值（如需调试可加回数值打印）
            print(f"[{timezone.now().strftime('%H:%M:%S')}] 数据入库成功: {device.name}")

        except Exception as e:
            logger.error(f"解析设备 {device.did} 数据时出错: {e}")