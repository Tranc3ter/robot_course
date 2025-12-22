import zmq
import json
import time
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
import io
import os
import sys

# 机器人控制相关
import hiwonder.ros_robot_controller_sdk as rrc
from gpiozero import Button

class RobotClient:
    def __init__(self, server_ip: str = "localhost"):
        self.server_ip = server_ip
        
        # 初始化ZMQ上下文
        self.context = zmq.Context()
        
        # 连接到各个服务器
        self.asr_socket = self.context.socket(zmq.REQ)
        self.asr_socket.connect(f"tcp://{server_ip}:5555")
        
        self.mcp_socket = self.context.socket(zmq.REQ)
        self.mcp_socket.connect(f"tcp://{server_ip}:5557")
        
        self.tts_socket = self.context.socket(zmq.REQ)
        self.tts_socket.connect(f"tcp://{server_ip}:5556")
        
        # 音频设置
        self.sample_rate = 48000
        self.channels = 1
        self.dtype = "int16"
        
        # 录音状态
        self.is_recording = False
        self.audio_data = []
        
        # 机器人控制
        self.board = rrc.Board()
        self.touch_button = Button(22)  # GPIO 22
        
        print(f"Robot Client connected to server at {server_ip}")
    
    def record_audio(self, duration: float = 3.0) -> bytes:
        """录制音频"""
        print(f"Recording for {duration} seconds...")
        
        # 录制音频
        audio = sd.rec(int(duration * self.sample_rate),
                      samplerate=self.sample_rate,
                      channels=self.channels,
                      dtype=self.dtype)
        sd.wait()
        
        # 转换为字节
        audio_bytes = audio.tobytes()
        return audio_bytes
    
    def send_to_asr(self, audio_bytes: bytes) -> str:
        """发送音频到ASR服务器"""
        try:
            # 发送音频数据
            request = json.dumps({
                'audio': audio_bytes.decode('latin-1'),
                'sample_rate': self.sample_rate
            })
            
            self.asr_socket.send_string(request)
            response = self.asr_socket.recv_string()
            result = json.loads(response)
            
            if result['status'] == 'success':
                return result['text']
            else:
                print(f"ASR Error: {result.get('error', 'Unknown error')}")
                return ""
                
        except Exception as e:
            print(f"ASR Communication error: {e}")
            return ""
    
    def send_to_mcp(self, text: str) -> str:
        """发送文本到MCP服务器"""
        try:
            request = json.dumps({
                'text': text
            })
            
            self.mcp_socket.send_string(request)
            response = self.mcp_socket.recv_json()
            
            if response['status'] == 'success':
                return response['response']
            else:
                print(f"MCP Error: {response.get('error', 'Unknown error')}")
                return ""
                
        except Exception as e:
            print(f"MCP Communication error: {e}")
            return ""
    
    def send_to_tts(self, text: str) -> bytes:
        """发送文本到TTS服务器，返回音频数据"""
        try:
            request = json.dumps({
                'text': text,
                'voice': 'zf_xiaobei'
            })
            
            self.tts_socket.send_string(request)
            response = self.tts_socket.recv_json()
            
            if response['status'] == 'success':
                # 将字符串转换回字节
                audio_bytes = response['audio'].encode('latin-1')
                return audio_bytes
            else:
                print(f"TTS Error: {response.get('error', 'Unknown error')}")
                return b""
                
        except Exception as e:
            print(f"TTS Communication error: {e}")
            return b""
    
    def play_audio(self, audio_bytes: bytes, sample_rate: int = 24000):
        """播放音频"""
        try:
            # 将字节转换为numpy数组
            audio_io = io.BytesIO(audio_bytes)
            audio_data, sr = sf.read(audio_io)
            
            # 播放音频
            sd.play(audio_data, sr)
            sd.wait()
            
        except Exception as e:
            print(f"Audio playback error: {e}")
    
    def conversation_cycle(self):
        """执行一次完整的对话循环"""
        print("\n" + "="*50)
        print("Starting conversation cycle...")
        
        # 1. 录制用户语音
        print("1. Recording user speech...")
        audio_bytes = self.record_audio(duration=3.0)
        
        # 2. 语音转文本
        print("2. Converting speech to text...")
        user_text = self.send_to_asr(audio_bytes)
        print(f"   User said: {user_text}")
        
        if not user_text:
            print("No speech detected or ASR failed.")
            return
        
        # 3. 生成回复
        print("3. Generating response...")
        response_text = self.send_to_mcp(user_text)
        print(f"   AI Response: {response_text}")
        
        if not response_text:
            print("No response generated.")
            return
        
        # 4. 文本转语音
        print("4. Converting response to speech...")
        audio_response = self.send_to_tts(response_text)
        
        # 5. 播放回复
        print("5. Playing response...")
        self.play_audio(audio_response)
        
        print("Conversation cycle completed!")
        print("="*50 + "\n")
    
    def button_monitor(self):
        """监控按钮状态"""
        print("Button monitor started. Press Ctrl+C to exit.")
        
        try:
            while True:
                # 检查按钮是否被按下
                if self.touch_button.is_pressed:
                    print("Button pressed! Starting conversation...")
                    
                    # 视觉反馈：闪烁蜂鸣器
                    for _ in range(3):
                        self.board.set_buzzer(1000, 0.1, 0.1, 1)
                        time.sleep(0.2)
                    
                    # 执行对话循环
                    self.conversation_cycle()
                    
                    time.sleep(1)  # 防抖动
                
                time.sleep(0.1)  # 降低CPU使用率
                
        except KeyboardInterrupt:
            print("Button monitor stopped.")
        finally:
            # 清理
            self.board.set_buzzer(1000, 0.0, 0.0, 1)
    
    def run(self):
        """运行机器人客户端"""
        print("Robot Client is running...")
        
        # 启动按钮监控（在主线程中运行）
        self.button_monitor()

if __name__ == "__main__":
    # 从命令行参数获取服务器IP，默认为localhost
    server_ip = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    
    client = RobotClient(server_ip=server_ip)
    client.run()