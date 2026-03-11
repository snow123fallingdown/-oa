import json
import logging
import threading
import time
import random  # 导入随机数工具
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction, OperationalError # 导入异常捕获
import paho.mqtt.client as mqtt

# 请确保导入路径与您的项目结构一致
from dvadmin.sensor.models import SensorDevice, SensorLog

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '分布式 MQTT 监听服务（死锁优化版）'

    KEY_MAPPING = {
        "T": "temperature", "HUM": "humidity", "Co2": "co2", "TVoc": "tvoc",
        "PM0.3": "pm03", "PM0.5": "pm05", "PM1": "pm1", "PM2.5": "pm25",
        "PM4": "pm4", "PM10": "pm10", "PM100": "pm100", 
        "O3": "o3", "So2": "so2", "No2": "no2", "CH2O": "ch2o",
        "Co": "co", "Pressure": "pressure", "RSSI": "rssi"
    }

    def handle(self, *args, **options):
        devices = SensorDevice.objects.filter(status=True)
        if not devices.exists():
            self.stdout.write(self.style.WARNING("未发现启用设备。"))
            return

        self.stdout.write(self.style.SUCCESS(f"--- 启动监听服务，共 {devices.count()} 个设备 ---"))

        for device in devices:
            t = threading.Thread(
                target=self.start_mqtt_worker, 
                args=(device,), 
                name=f"Thread-{device.did}"
            )
            t.daemon = True
            t.start()
            self.stdout.write(f"  > [ {device.name} ] 监听线程已就绪")

        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("\n服务已手动停止"))

    def start_mqtt_worker(self, device):
        client_id = f"SINK_{device.did}_{str(int(time.time()))[-4:]}"
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id)
        except AttributeError:
            client = mqtt.Client(client_id=client_id)

        client.on_connect = lambda c, u, f, rc: self.on_connect(c, u, f, rc, device)
        client.on_message = lambda c, u, m: self.on_message(c, u, m, device)

        while True:
            try:
                client.connect(
                    host=getattr(device, 'broker_ip', '127.0.0.1'), 
                    port=int(getattr(device, 'broker_port', 1883)), 
                    keepalive=60
                )
                client.loop_forever()
            except Exception:
                logger.error(f"设备 [{device.name}] 连接异常，15秒后重试...")
                time.sleep(15)

    def on_connect(self, client, userdata, flags, rc, device):
        if rc == 0:
            topic = getattr(device, 'subscribe_topic', '/device/sensors')
            client.subscribe(topic)
            self.stdout.write(self.style.SUCCESS(f" [√] {device.name} 已连接"))
        else:
            logger.error(f" [×] {device.name} 连接失败，错误码: {rc}")

    def on_message(self, client, userdata, msg, device):
        """
        优化后的消息处理：降低清理频率以避免死锁
        """
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            sensors = payload.get("sensor", [])
            
            db_data = {
                "tl": payload.get("TL"),
                "device": device,
                "create_datetime": timezone.now()
            }

            for item in sensors:
                raw_key = str(item.get("2", "")).strip()
                field_name = self.KEY_MAPPING.get(raw_key)
                if field_name:
                    db_data[field_name] = item.get("3")

            # 1. 核心入库操作（最高优先级）
            try:
                with transaction.atomic():
                    SensorLog.objects.create(**db_data)
                    SensorDevice.objects.filter(pk=device.pk).update(last_online=timezone.now())
            except OperationalError as e:
                if 'Deadlock' in str(e):
                    logger.warning(f"检测到入库死锁，跳过本次入库: {device.name}")
                    return

            # 2. 概率性清理逻辑（避免所有线程同时执行 DELETE）
            # 只有 10% 的概率执行清理，极大地降低了死锁风险
            if random.random() < 0.1:
                self.perform_cleanup(device)

            print(f"[{timezone.now().strftime('%H:%M:%S')}] {device.name}: 更新成功")

        except Exception as e:
            logger.error(f"解析设备 {device.did} 数据时出错: {e}")

    def perform_cleanup(self, device):
        """
        独立清理函数，增加死锁捕获
        """
        try:
            # 这种做法不放在大的事务里，减少锁定时间
            keep_ids = list(SensorLog.objects.filter(device=device)
                            .order_by('-create_datetime')[:10]
                            .values_list('id', flat=True))
            
            if keep_ids:
                # 排除法删除旧记录
                SensorLog.objects.filter(device=device).exclude(id__in=keep_ids).delete()
        except OperationalError as e:
            if 'Deadlock' in str(e):
                # 如果清理时发生死锁，直接放弃，等下次概率触发即可
                pass