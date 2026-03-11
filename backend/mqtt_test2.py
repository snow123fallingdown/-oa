import json
import random
import time
from datetime import datetime
import paho.mqtt.client as mqtt

# === 配置区域 ===
BROKER = "127.0.0.1" 
PORT = 1883
DEFAULT_TOPIC = "/device/sensors"
CLIENT_ID = f"SIMULATOR_MASTE3213213R_{int(time.time())}" 
INTERVAL = 5  # 缩短间隔到5秒，方便观察随机波动

# 🔴 设备列表
DEVICE_LIST = [
    
    {"did": "篮球场传感器22222", "temp_range": (28.0, 32.0), "pm_range": (50, 80)},
]

# === 真正的随机数据生成器 ===
def generate_payload(device_config):
    """
    基于设备配置生成随机波动数据
    """
    did = device_config["did"]
    t_min, t_max = device_config["temp_range"]
    p_min, p_max = device_config["pm_range"]

    # 核心：完全随机，没有任何 seed 锁定
    data = {
        "DID": did,
        "TL": -1,
        "sensor": [
            # 温度：范围内随机浮点
            {"2": "T",          "3": round(random.uniform(t_min, t_max), 2)},
            # 湿度：30-70% 随机
            {"2": "HUM",        "3": round(random.uniform(30.0, 70.0), 1)},
            # 气压：标准大气压附近波动
            {"2": "Pressure",   "3": random.randint(101000, 101325)},
            # PM2.5：基于设备特定范围随机
            {"2": "PM2.5",      "3": round(random.uniform(p_min, p_max), 1)},
            # 二氧化碳：400-1200 随机
            {"2": "Co2",        "3": random.randint(400, 1200)},
            # TVoc：微量随机
            {"2": "TVoc",       "3": round(random.uniform(0.001, 0.500), 3)},
            # 信号强度：-40 到 -90 之间
            {"2": "RSSI",       "3": random.randint(-90, -40)},
        ]
    }
    return data

# === 主运行逻辑 ===
def start_simulation():
    client = mqtt.Client(client_id=CLIENT_ID)
    
    try:
        print(f"--- 实时随机模拟器启动 ---")
        client.connect(BROKER, PORT, 60)
        client.loop_start() 
        
        while True:
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f"\n[{current_time}] 🚀 发布随机数据轮次...")
            
            for config in DEVICE_LIST:
                payload = generate_payload(config)
                payload_str = json.dumps(payload)
                
                # --- 修改点在这里 ---
                # qos=1: 保证消息传递质量
                # retain=True: 监听脚本启动时，会立即收到最新的这条数据，不用等下一个5秒循环
                client.publish(DEFAULT_TOPIC, payload_str, qos=1, retain=True)
                # ------------------
                
                temp = payload['sensor'][0]['3']
                pm25 = payload['sensor'][3]['3']
                
                print(f" >> {config['did']:<12} | 温度: {temp}℃ | PM2.5: {pm25}")
                time.sleep(0.05) 

            time.sleep(INTERVAL)
    # ... 其余代码保持不变

    except KeyboardInterrupt:
        print("\n模拟器停止")
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    start_simulation()