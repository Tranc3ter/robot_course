import threading
import time
import sys
import os

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from servers.asr_server import ASRServer
from servers.tts_server import TTSServer
from servers.mcp_server import MCPServer

def run_asr_server():
    """运行ASR服务器"""
    print("启动ASR服务器...")
    server = ASRServer(port=5555)
    server.run()

def run_tts_server():
    """运行TTS服务器"""
    print("启动TTS服务器...")
    server = TTSServer(port=5556)
    server.run()

def run_mcp_server():
    """运行MCP服务器"""
    print("启动MCP服务器...")
    server = MCPServer(port=5557)
    server.run()

def get_windows_ip():
    """获取Windows IP地址"""
    import socket
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        return ip_address
    except:
        return "0.0.0.0"

def main():
    """启动所有服务器"""
    print("=" * 60)
    print("启动所有机器人服务器")
    print("=" * 60)
    
    # 获取Windows IP地址
    windows_ip = get_windows_ip()
    print(f"Windows IP地址: {windows_ip}")
    
    # 创建并启动服务器线程
    threads = []
    
    # ASR服务器线程
    asr_thread = threading.Thread(target=run_asr_server, daemon=True)
    threads.append(asr_thread)
    
    # TTS服务器线程
    tts_thread = threading.Thread(target=run_tts_server, daemon=True)
    threads.append(tts_thread)
    
    # MCP服务器线程
    mcp_thread = threading.Thread(target=run_mcp_server, daemon=True)
    threads.append(mcp_thread)
    
    # 启动所有线程
    print("\n启动服务器...")
    for thread in threads:
        thread.start()
        time.sleep(1)  # 间隔启动
    
    print("\n" + "=" * 60)
    print("所有服务器已启动！")
    print("=" * 60)
    print(f"ASR Server: tcp://{windows_ip}:5555")
    print(f"TTS Server: tcp://{windows_ip}:5556")
    print(f"MCP Server: tcp://{windows_ip}:5557")
    print("=" * 60)
    print("\n重要提示:")
    print("1. 确保Windows防火墙允许端口5555-5557")
    print("2. 树莓派客户端需使用上述IP地址连接")
    print("3. 按 Ctrl+C 停止所有服务器")
    print("=" * 60)
    
    # 保持主线程运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在关闭服务器...")

if __name__ == "__main__":
    main()