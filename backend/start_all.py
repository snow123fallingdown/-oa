import subprocess
import sys
import time
import os

def run_services():
    # 获取当前 Python 解释器的路径 (确保使用虚拟环境)
    python_exe = sys.executable

    # 定义要运行的命令
    # 注意：请确保 'mqtt_listener' 是你实际的命令文件名，如果改名叫 mqtt_start 了就填 mqtt_start
    cmd_server = [python_exe, "manage.py", "runserver", "0.0.0.0:8000"]
    cmd_mqtt = [python_exe, "manage.py", "mqtt_start"] 

    print("--- 正在启动 Django 服务和 MQTT 监听 ---")
    
    try:
        # Popen 会异步启动子进程，不会阻塞当前脚本
        # creationflags=subprocess.CREATE_NEW_CONSOLE 会在 Windows 下弹出新窗口 (可选)
        # 如果想都在一个窗口输出，去掉 creationflags 参数即可
        
        # 启动 MQTT
        p_mqtt = subprocess.Popen(cmd_mqtt)
        print(f"> MQTT 服务已启动 (PID: {p_mqtt.pid})")
        
        # 等待一秒，防止输出混在一起
        time.sleep(1)

        # 启动 Web Server
        p_server = subprocess.Popen(cmd_server)
        print(f"> Web Server 已启动 (PID: {p_server.pid})")

        print("--- 服务运行中，按 Ctrl+C 停止所有服务 ---")
        
        # 保持主进程运行，直到用户按下 Ctrl+C
        p_server.wait()
        p_mqtt.wait()

    except KeyboardInterrupt:
        print("\n--- 正在停止所有服务 ---")
        # 杀掉子进程（检查变量是否存在）
        if 'p_mqtt' in locals():
            p_mqtt.terminate()
        if 'p_server' in locals():
            p_server.terminate()
        print("已停止。")

if __name__ == "__main__":
    run_services()