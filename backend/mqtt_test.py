import json
import random
import time
from datetime import datetime
import paho.mqtt.client as mqtt

# === 配置区域 ===
BROKER = "127.0.0.1"
PORT = 1883
TOPIC = "/device/sensors"
CLIENT_ID = f"Multi_Sender_{int(time.time())}" 
INTERVAL = 10  # 发送间隔（秒）：每轮发送后的等待时间

# 🔴在此处定义你要模拟的所有设备 ID
DEVICE_LIST = [
    "TEST-1",
    "TEST-2",
    "123456",
    "551135"
]

# === 模拟数据生成器 ===
def generate_payload(device_id):
    """
    生成符合完整协议的测试数据
    :param device_id: 当前设备的 DID
    """
    
    # 模拟不同设备可能处于略微不同的环境，这里依旧使用随机波动
    data = {
        "DID": device_id,    # 🔴 使用传入的 device_id
        "TL": -1,            # 订阅剩余时间
        "sensor": [
            # --- 核心环境 ---
            {"2": "T",          "3": round(random.uniform(20.0, 30.0), 1)},
            {"2": "HUM",        "3": round(random.uniform(30.0, 70.0), 1)},
            {"2": " Pressure ", "3": random.randint(100000, 101325)},

            # --- PM 颗粒物 ---
            {"2": "PM0.3",      "3": round(random.uniform(5, 15), 1)},
            {"2": "PM0.5",      "3": round(random.uniform(10, 20), 1)},
            {"2": "PM1",        "3": round(random.uniform(15, 25), 1)},
            {"2": "PM2.5",      "3": round(random.uniform(20, 60), 1)}, 
            {"2": "PM4",        "3": round(random.uniform(30, 70), 1)},
            {"2": "PM10",       "3": round(random.uniform(40, 90), 1)},
            {"2": "PM100",      "3": round(random.uniform(50, 110), 1)},

            # --- 气体与有机物 ---
            {"2": "Co2",        "3": random.randint(400, 1500)},
            {"2": "TVoc",       "3": round(random.uniform(0.01, 0.5), 3)},
            {"2": "CH2O",       "3": round(random.uniform(0.01, 0.08), 3)},
            {"2": "Co",         "3": round(random.uniform(0.1, 1.2), 2)},
            
            # --- 有害气体 ---
            {"2": "O3",         "3": round(random.uniform(20, 80), 1)},
            {"2": "So2",        "3": round(random.uniform(5, 30), 1)},
            {"2": "No2",        "3": round(random.uniform(10, 40), 1)},

            # --- 设备状态 ---
            {"2": "RSSI",       "3": random.randint(10, 31)},
        ]
    }
    return data

# === 主运行逻辑 ===
def start_simulation():
    client = mqtt.Client(client_id=CLIENT_ID)
    
    try:
        print(f"正在连接到 MQTT Broker ({BROKER})...")
        client.connect(BROKER, PORT, 60)
        client.loop_start() 
        
        print(f"连接成功！模拟设备数: {len(DEVICE_LIST)}")
        print(f"设备列表: {DEVICE_LIST}")
        print("-" * 50)

        while True:
            print(f"\n--- [ {datetime.now().strftime('%H:%M:%S')} ] 开始新一轮发送 ---")
            
            # 🔴 遍历每一个设备
            for did in DEVICE_LIST:
                # 1. 生成该设备的数据
                payload = generate_payload(did)
                payload_str = json.dumps(payload)
                
                # 2. 发布消息
                client.publish(TOPIC, payload_str)
                
                # 获取关键指标用于日志显示
                pm25 = next((item['3'] for item in payload['sensor'] if item['2'] == 'PM2.5'), 0)
                temp = next((item['3'] for item in payload['sensor'] if item['2'] == 'T'), 0)
                
                print(f" >> 发送成功: {did:<20} | 温度: {temp} | PM2.5: {pm25}")
                
                # 为了防止瞬间并发过高，每个设备之间稍微停顿 0.2秒
                time.sleep(0.2)

            print(f"--- 本轮发送完毕，等待 {INTERVAL} 秒 ---")
            # 3. 等待下一轮
            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print("\n\n>>> 用户停止脚本")
        client.loop_stop()
        client.disconnect()
    except Exception as e:
        print(f"\n!!! 发生错误: {e}")
        client.loop_stop()

if __name__ == "__main__":
    start_simulation()