import json
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
import paho.mqtt.client as mqtt

#启动命令：cd backend  python manage.py mqtt_start


# 注意：确保你的 app 名字是 'dvadmin.sensor' (根据 apps.py 的配置)
from dvadmin.sensor.models import SensorDevice, SensorLog

# === 配置区域 (建议后续移到 settings.py) ===
MQTT_BROKER = "127.0.0.1"   # MQTT服务器地址
MQTT_PORT = 1883            # 端口
MQTT_TOPIC = "/device/sensors"  # 订阅主题
MQTT_CLIENT_ID = "Django_OA_Listener_01" # 客户端ID，保持唯一
MQTT_USER = ""              # 如果有账号密码请在此填写
MQTT_PASSWORD = ""

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '启动 MQTT 传感器数据监听服务'

    # 协议 Key 到 数据库字段 Field 的映射表
    # Key: 协议中 "2" 对应的值 (已去除空格)
    # Value: SensorLog 模型中的字段名
    KEY_MAPPING = {
        "T": "temperature",
        "HUM": "humidity",
        "Co2": "co2",
        "TVoc": "tvoc",
        "PM0.3": "pm03", # 如果模型里没定义这些细分PM，可以注释掉
        "PM0.5": "pm05",
        "PM1": "pm1",
        "PM2.5": "pm25",
        "PM4": "pm4",
        "PM10": "pm10",
        "PM100": "pm100",
        "O3": "o3",
        "RSSI": "rssi",
        "So2": "so2",
        "No2": "no2",
        "CH2O": "ch2o",
        "Co": "co",
        "Pressure": "pressure",
        "Run counter": "run_counter"
    }

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(f"--- 正在启动 MQTT 监听服务 ---"))
        self.stdout.write(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
        self.stdout.write(f"Topic:  {MQTT_TOPIC}")

        client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        
        # 如果有账号密码
        if MQTT_USER and MQTT_PASSWORD:
            client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

        # 绑定回调函数
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.on_disconnect = self.on_disconnect

        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            # 阻塞运行，保持监听
            client.loop_forever()
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("用户手动停止监听"))
            client.disconnect()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"连接发生严重错误: {e}"))

    def on_connect(self, client, userdata, flags, rc):
        """连接成功回调"""
        if rc == 0:
            self.stdout.write(self.style.SUCCESS('>>> MQTT 连接成功'))
            client.subscribe(MQTT_TOPIC)
            self.stdout.write(f'>>> 已订阅主题: {MQTT_TOPIC}')
        else:
            self.stdout.write(self.style.ERROR(f'>>> 连接失败，返回码: {rc}'))

    def on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        if rc != 0:
            self.stdout.write(self.style.WARNING(">>> 意外断开连接，正在尝试重连..."))

    def on_message(self, client, userdata, msg):
        """接收消息核心逻辑"""
        try:
            payload_str = msg.payload.decode('utf-8')
            # 1. JSON 解析
            data = json.loads(payload_str)
            
            # 2. 提取基础信息
            did = data.get("DID")
            tl = data.get("TL")
            sensors = data.get("sensor", [])

            if not did:
                logger.warning("接收到无效数据: 缺少 DID")
                return

            # 3. 核心业务：设备关联 (自动注册策略)
            # 查找设备，如果不存在则创建
            device_obj, created = SensorDevice.objects.get_or_create(
                did=did,
                defaults={
                    'name': f"检测仪-{did}",  # 默认名称
                    'location': "未分配位置",
                    'status': True
                }
            )

            if created:
                self.stdout.write(self.style.NOTICE(f"发现新设备并自动注册: {did}"))

            # 4. 数据解析
            db_data = {
                "tl": tl
            }

            for item in sensors:
                raw_key = item.get("2")  # 例如 " Pressure " 或 "T"
                value = item.get("3")    # 数值

                if raw_key:
                    # 去除首尾空格，这点很重要，因为协议里有空格
                    clean_key = raw_key.strip()
                    
                    # 匹配数据库字段
                    field_name = self.KEY_MAPPING.get(clean_key)
                    
                    if field_name:
                        # 可以在这里做简单的数据清洗，例如防止None
                        db_data[field_name] = value

            # 5. 保存数据到 SensorLog 表
            # 注意：SensorDevice 是 CoreModel，SensorLog 也是 CoreModel
            # CoreModel 会自动处理 create_datetime, update_datetime, creator 等字段
            # 但在这里是脚本运行，没有 request.user，CoreModel 可能会有些字段为空，这是正常的
            log_obj = SensorLog.objects.create(
                device=device_obj,
                **db_data
            )
            
            # 6. (可选) 简易控制台输出，证明在干活
            print(f"[{log_obj.create_datetime.strftime('%H:%M:%S')}] {did} | T:{db_data.get('temperature')} | PM2.5:{db_data.get('pm25')}")

            # 7. (可选) 简单的告警触发逻辑
            self.check_alert(device_obj, db_data)

        except json.JSONDecodeError:
            logger.error(f"JSON 解析失败: {payload_str}")
        except Exception as e:
            logger.error(f"处理消息时发生未知错误: {e}")

    def check_alert(self, device, data):
        """简单的告警检查逻辑"""
        try:
            pm25 = data.get('pm25')
            # 假设你在 SensorDevice 模型里加了 alert_pm25 字段
            threshold = getattr(device, 'alert_pm25', 75.0) 

            if pm25 and pm25 > threshold:
                msg = f"警告: 设备 {device.name} PM2.5 超标! 当前值: {pm25}"
                self.stdout.write(self.style.ERROR(msg))
                # 可以在这里调用 OA 的消息通知函数
                # from dvadmin.system.models import Message
                # ...
        except Exception as e:
            pass