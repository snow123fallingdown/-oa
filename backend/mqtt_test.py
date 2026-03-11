import json
import random
import time
from datetime import datetime
import paho.mqtt.client as mqtt

# === 配置区域 ===
BROKER = "127.0.0.1" 
PORT = 1883
DEFAULT_TOPIC = "/device/sensors"
# 保持 Client ID 唯一
CLIENT_ID = f"SIMULATOR_MSD_{int(time.time())}" 
INTERVAL = 5 

# 🔴 设备列表：DID 格式改为 MSD-xxxxxxxx
DEVICE_LIST = [

    {"did": "TEST-1", "temp_range": (22.0, 24.0), "pm_range": (10, 30)},

    {"did": "TEST-2", "temp_range": (25.0, 27.0), "pm_range": (40, 60)},

    {"did": "123456", "temp_range": (18.0, 21.0), "pm_range": (5, 15)},

    {"did": "551135", "temp_range": (20.0, 22.0), "pm_range": (20, 45)},

    {"did": "篮球场传感器", "temp_range": (28.0, 32.0), "pm_range": (50, 80)},

]

def generate_payload(device_config):
    """
    生成完全符合你所提供 JSON 格式的数据
    """
    did = device_config["did"]
    t_min, t_max = device_config["temp_range"]
    p_min, p_max = device_config["pm_range"]

    # 构造符合协议的列表
    data = {
        "DID": did,
        "TL": -1,
        "sensor": [
            {"2": "T",           "3": round(random.uniform(t_min, t_max), 1)},
            {"2": "HUM",         "3": round(random.uniform(30.0, 50.0), 2)},
            {"2": "Co2",         "3": random.randint(400, 700)},
            {"2": "TVoc",        "3": round(random.uniform(0.05, 0.15), 3)},
            {"2": "PM0.3",       "3": round(random.uniform(p_min, p_max), 1)},
            {"2": "PM0.5",       "3": round(random.uniform(p_min, p_max), 1)},
            {"2": "PM1",         "3": round(random.uniform(p_min, p_max), 1)},
            {"2": "PM2.5",       "3": round(random.uniform(p_min, p_max), 1)},
            {"2": "PM4",         "3": round(random.uniform(p_min, p_max), 1)},
            {"2": "PM10",        "3": round(random.uniform(p_min, p_max), 1)},
            {"2": "PM100",       "3": round(random.uniform(p_min, p_max), 1)},
            {"2": "O3",          "3": random.randint(0, 10)},
            {"2": "RSSI",        "3": random.randint(20, 31)},
            {"2": "So2",         "3": random.randint(20, 50)},
            {"2": "No2",         "3": random.randint(10, 30)},
            {"2": "CH2O",        "3": round(random.uniform(0.08, 0.12), 3)},
            {"2": "Co",          "3": round(random.uniform(0.001, 0.01), 3)},
            {"2": " Pressure ",  "3": random.randint(10000, 12000)}, # 注意前后的空格
            {"2": "Run counter", "3": random.randint(100, 1000)}
        ]
    }
    return data

def start_simulation():
    # 适配 Paho-MQTT 2.0+，同时兼容 1.x
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=CLIENT_ID)
    except AttributeError:
        client = mqtt.Client(client_id=CLIENT_ID)
    
    try:
        print(f"--- 协议适配版模拟器启动 ---")
        print(f"目标端口: {PORT}")
        client.connect(BROKER, PORT, 60)
        client.loop_start() 
        
        while True:
            current_time = datetime.now().strftime('%H:%M:%S')
            for config in DEVICE_LIST:
                payload = generate_payload(config)
                payload_str = json.dumps(payload)
                
                # 发布
                client.publish(DEFAULT_TOPIC, payload_str, qos=1)
                
                print(f"[{current_time}] 已推送数据: {config['did']} -> 1883")
                time.sleep(0.05) 

            time.sleep(INTERVAL)
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    start_simulation()