# asr_server.py
import zmq
import numpy as np
import json
import traceback
import queue
import threading
import time
import os
import sys
from datetime import datetime
from typing import Dict, Optional, Any

try:
    import sounddevice as sd
except ImportError:
    sd = None

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
print(f"当前目录: {current_dir}")

# 尝试多种可能的项目根目录
possible_roots = [
    os.path.dirname(current_dir),  # w08
    os.path.dirname(os.path.dirname(current_dir)),  # robot_course
    os.path.join(os.path.dirname(current_dir), "robot-course"),  # robot-course
    r"C:\Users\31702\Documents\programme\robot_course\robot-course"
]

ASR_AVAILABLE = False
SpeechRecognizer = None

# 尝试找到正确的路径并导入
for project_root in possible_roots:
    funasr_path = os.path.join(project_root, "src", "w04", "s05_funasr.py")
    print(f"检查路径: {funasr_path}")
    
    if os.path.exists(funasr_path):
        print(f"✓ 找到文件: {funasr_path}")
        try:
            # 将项目根目录添加到系统路径
            if project_root not in sys.path:
                sys.path.append(project_root)
            
            # 尝试导入
            import importlib.util
            spec = importlib.util.spec_from_file_location("s05_funasr", funasr_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            SpeechRecognizer = module.SpeechRecognizer
            ASR_AVAILABLE = True
            print(f"✓ 成功导入SpeechRecognizer")
            break
        except Exception as e:
            print(f"✗ 导入失败: {e}")
            traceback.print_exc()
    else:
        print(f"✗ 文件不存在: {funasr_path}")

# 如果上面的方法失败，尝试直接指定路径
if not ASR_AVAILABLE:
    funasr_direct_path = r"C:\Users\31702\Documents\programme\robot_course\robot-course\src\w04\s05_funasr.py"
    print(f"尝试直接路径: {funasr_direct_path}")
    
    if os.path.exists(funasr_direct_path):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("s05_funasr", funasr_direct_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            SpeechRecognizer = module.SpeechRecognizer
            ASR_AVAILABLE = True
            print(f"✓ 成功导入SpeechRecognizer (直接路径)")
        except Exception as e:
            print(f"✗ 导入失败: {e}")
            traceback.print_exc()
    else:
        print(f"✗ 直接路径文件也不存在")

if not ASR_AVAILABLE:
    print("⚠ 将使用模拟模式")


class ASRServer:
    """
    ASR服务器类 - ZMQ版本
    专门适配您的SpeechRecognizer接口
    """

    def __init__(self, port: int = 5555, audio_output: bool = False, queue_size: int = 50):
        """
        初始化ASR服务器

        Args:
            port (int): 服务器监听端口
            audio_output (bool): 是否播放接收到的音频（调试用）
            queue_size (int): 音频队列大小
        """
        self.port = port
        self.audio_output = audio_output
        self.queue_size = queue_size

        # ZMQ设置
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.bind(f"tcp://0.0.0.0:{port}")

        # 状态变量
        self._running = False

        # 初始化ASR识别器
        if ASR_AVAILABLE and SpeechRecognizer is not None:
            try:
                self.recognizer = SpeechRecognizer()
                print("✓ SpeechRecognizer初始化成功")
                # 尝试访问属性（如果存在）
                try:
                    print(f"  模型目录: {self.recognizer.model_dir}")
                except:
                    pass
                try:
                    print(f"  采样率: {self.recognizer.SAMPLE_RATE}Hz")
                except:
                    pass
            except Exception as e:
                print(f"✗ SpeechRecognizer初始化失败: {e}")
                traceback.print_exc()
                self.recognizer = None
        else:
            self.recognizer = None
            print("⚠ ASR服务器运行在模拟模式")
        
        # 结果存储
        self._recognition_results = {}
        self._latest_result = None
        
        # 用于同步访问的锁
        self._result_lock = threading.Lock()
        
        # 音频输出流
        self.audio_stream = None
        
        print(f"ASR服务器初始化完成，监听端口 {port}")
        print("=" * 60)

    def start(self):
        """启动ASR服务器"""
        if self._running:
            print("ASR服务器已经在运行中")
            return

        self._running = True
        
        if self.audio_output and sd is None:
            print("⚠ 未安装 'sounddevice'，音频播放功能已禁用")
            self.audio_output = False

        print("✓ ASR服务器已启动")
        print(f"   模式: {'真实ASR' if self.recognizer is not None else '模拟'}")
        print(f"   音频输出: {'启用' if self.audio_output else '禁用'}")
        
        # 启动主服务器循环
        self._run_server()

    def stop(self):
        """停止ASR服务器"""
        if not self._running:
            return

        print("正在停止ASR服务器...")
        self._running = False

        # 停止音频流
        if self.audio_stream:
            try:
                self.audio_stream.stop()
                self.audio_stream = None
            except:
                pass

        # 关闭ZMQ socket
        self.socket.close()
        self.context.term()

        print("✓ ASR服务器已完全停止")

    def _run_server(self):
        """运行ZMQ服务器主循环"""
        poller = zmq.Poller()
        poller.register(self.socket, zmq.POLLIN)
        
        print("等待客户端连接...")
        
        while self._running:
            try:
                events = dict(poller.poll(timeout=100))  # 100ms超时
                
                if self.socket in events:
                    # 接收并处理请求
                    try:
                        # 接收请求
                        message = self.socket.recv()
                        
                        # 处理请求并获取响应
                        response = self._handle_client_request(message)
                        
                        # 发送响应
                        self.socket.send_string(response)
                        
                    except Exception as e:
                        print(f"✗ 处理请求错误: {e}")
                        traceback.print_exc()
                        error_response = json.dumps({
                            'text': '',
                            'status': 'error',
                            'error': str(e),
                            'timestamp': time.time()
                        })
                        self.socket.send_string(error_response)
                
            except KeyboardInterrupt:
                print("\n收到中断信号，正在关闭服务器...")
                break
            except Exception as e:
                if self._running:
                    print(f"✗ 服务器错误: {e}")
                    traceback.print_exc()

    def _handle_client_request(self, message: bytes) -> str:
        """处理客户端请求"""
        start_time = time.time()
        
        try:
            # 解析JSON消息
            try:
                data = json.loads(message.decode('utf-8'))
                audio_base64 = data.get('audio', '')
                sample_rate = data.get('sample_rate', 48000)
                
                # 将base64字符串解码为音频字节
                audio_bytes = audio_base64.encode('latin-1')
                audio_length = len(audio_bytes)
                print(f"[ASR] 收到音频数据: {audio_length} 字节, 采样率: {sample_rate}Hz")
                
            except json.JSONDecodeError:
                # 如果不是JSON，可能是原始音频数据
                audio_bytes = message
                sample_rate = 48000
                audio_length = len(audio_bytes)
                print(f"[ASR] 收到原始音频数据: {audio_length} 字节")
            
            # 执行ASR识别
            if self.recognizer is not None:
                text = self._perform_real_asr(audio_bytes, sample_rate)
            else:
                text = self._perform_simulated_asr(audio_bytes, sample_rate)
            
            # 存储结果
            timestamp = time.time()
            with self._result_lock:
                self._latest_result = text
                self._recognition_results[timestamp] = text
            
            processing_time = time.time() - start_time
            print(f"[ASR] 识别完成: {text[:50]}... (处理时间: {processing_time:.2f}s)")
            
            # 构建响应
            response = json.dumps({
                'text': text,
                'status': 'success',
                'timestamp': timestamp,
                'audio_length': audio_length,
                'processing_time': processing_time
            })
            
            return response
                
        except Exception as e:
            print(f"✗ 处理请求失败: {e}")
            traceback.print_exc()
            return json.dumps({
                'text': '',
                'status': 'error',
                'error': str(e),
                'timestamp': time.time()
            })

    def _perform_real_asr(self, audio_bytes: bytes, sample_rate: int) -> str:
        """使用真实SpeechRecognizer执行ASR识别"""
        try:
            # 转换音频数据为numpy数组
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
            
            # 打印调试信息
            audio_duration = len(audio_data) / sample_rate
            print(f"  音频数据: {len(audio_data)}采样点, 时长: {audio_duration:.2f}秒")
            
            # 检查音频是否为空
            if len(audio_data) == 0:
                return "音频为空"
            
            # 调用SpeechRecognizer的识别方法
            print("  开始语音识别...")
            start_time = time.time()
            
            # 调用start_reco_with_audio方法
            self.recognizer.start_reco_with_audio(audio_data)
            
            # 等待一段时间让识别器处理
            time.sleep(0.3)  # 给ASR一些处理时间
            
            # 尝试获取识别结果
            text = ""
            
            # 首先检查temp_text
            if hasattr(self.recognizer, 'temp_text') and self.recognizer.temp_text:
                text = self.recognizer.temp_text
                print(f"  从temp_text获取结果: {text}")
            
            # 然后检查recognition_res
            elif hasattr(self.recognizer, 'recognition_res'):
                results = self.recognizer.recognition_res
                if results:
                    # 获取最新的结果
                    latest_timestamp = max(results.keys())
                    text = results[latest_timestamp]
                    print(f"  从recognition_res获取结果: {text}")
            
            # 如果都没有，尝试生成最终结果
            if not text:
                try:
                    if hasattr(self.recognizer, '_generate_final'):
                        final_res = self.recognizer._generate_final()
                        if final_res and len(final_res) > 0 and 'text' in final_res[0]:
                            text = final_res[0]['text']
                            print(f"  从_generate_final获取结果: {text}")
                except Exception as e:
                    print(f"  调用_generate_final失败: {e}")
            
            # 如果还是没有结果
            if not text:
                text = "未识别到语音内容"
                print("  未识别到语音内容")
            
            processing_time = time.time() - start_time
            print(f"  识别耗时: {processing_time:.2f}秒")
            
            return text
            
        except Exception as e:
            print(f"✗ 真实ASR识别失败: {e}")
            traceback.print_exc()
            return f"ASR识别错误: {str(e)}"

    def _perform_simulated_asr(self, audio_bytes: bytes, sample_rate: int) -> str:
        """模拟ASR识别"""
        try:
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
            duration = len(audio_data) / sample_rate
            
            # 模拟一些常见的语音识别结果
            simulated_texts = [
                "你好，我是智能语音助手",
                "请问有什么可以帮助你的吗",
                "今天的天气很好，适合外出",
                "人工智能技术正在快速发展",
                "树莓派是一个很好的学习平台",
                "语音识别技术越来越准确了",
                "欢迎使用语音交互系统"
            ]
            
            # 根据音频长度选择结果
            if len(audio_data) == 0:
                return "音频数据为空"
            
            idx = min(len(audio_data) // 1000, len(simulated_texts) - 1)
            text = f"[模拟] {simulated_texts[idx]} (音频时长: {duration:.2f}秒)"
            
            print(f"  模拟识别: {text}")
            return text
            
        except Exception as e:
            print(f"✗ 模拟ASR识别失败: {e}")
            return f"模拟识别错误: {str(e)}"

    def _play_audio(self, audio_bytes: bytes, sample_rate: int):
        """播放音频（如果启用）"""
        try:
            if self.audio_output and sd is not None:
                if self.audio_stream is None:
                    self.audio_stream = sd.OutputStream(
                        samplerate=sample_rate, 
                        channels=1, 
                        dtype="int16"
                    )
                    self.audio_stream.start()
                
                audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
                self.audio_stream.write(audio_data)
                
        except Exception as e:
            print(f"[ASR] 播放音频错误: {e}")
            self.audio_output = False
            if self.audio_stream:
                self.audio_stream.stop()
                self.audio_stream = None

    def get_latest_result(self) -> Optional[str]:
        """获取最新的识别结果"""
        with self._result_lock:
            return self._latest_result

    def get_recognition_results(self) -> Dict[float, str]:
        """获取所有识别结果"""
        with self._result_lock:
            return self._recognition_results.copy()

    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self
    def run(self):
        """运行服务器（兼容run_server.py的调用）"""
        self.start()
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()


def run_asr_server():
    """运行ASR服务器（兼容run_server.py）"""
    print("=" * 60)
    print("ASR服务器启动中...")
    print("=" * 60)
    
    server = ASRServer(port=5555, audio_output=False)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n正在停止服务器...")
    except Exception as e:
        print(f"服务器运行错误: {e}")
        traceback.print_exc()
    finally:
        server.stop()


def test_asr():
    """测试ASR功能"""
    print("测试ASR功能...")
    
    if ASR_AVAILABLE and SpeechRecognizer is not None:
        try:
            recognizer = SpeechRecognizer()
            print("✓ SpeechRecognizer创建成功")
            
            # 尝试访问属性
            if hasattr(recognizer, 'model_dir'):
                print(f"  模型目录: {recognizer.model_dir}")
            if hasattr(recognizer, 'SAMPLE_RATE'):
                print(f"  采样率: {recognizer.SAMPLE_RATE}Hz")
            
            # 测试一个简单的音频
            test_audio = np.random.randint(-1000, 1000, 48000, dtype=np.int16)  # 1秒的随机噪声
            print(f"  测试音频: {len(test_audio)}采样点")
            
            # 测试识别
            recognizer.start_reco_with_audio(test_audio)
            time.sleep(0.5)
            
            # 检查结果
            if hasattr(recognizer, 'temp_text'):
                print(f"  临时文本: {recognizer.temp_text}")
            
            if hasattr(recognizer, 'recognition_res'):
                results = recognizer.recognition_res
                if results:
                    print(f"  识别结果: {results}")
                else:
                    print("  无识别结果")
            
            print("✓ ASR测试完成")
                
        except Exception as e:
            print(f"✗ 测试失败: {e}")
            traceback.print_exc()
    else:
        print("⚠ 运行在模拟模式，无法测试真实ASR")


if __name__ == "__main__":
    # 测试或直接运行
    import argparse
    
    parser = argparse.ArgumentParser(description='ASR服务器')
    parser.add_argument('--test', action='store_true', help='测试ASR功能')
    parser.add_argument('--port', type=int, default=5555, help='服务器端口')
    
    args = parser.parse_args()
    
    if args.test:
        test_asr()
    else:
        print(f"启动ASR服务器，端口: {args.port}")
        server = ASRServer(port=args.port, audio_output=False)
        try:
            server.start()
        except KeyboardInterrupt:
            print("\n服务器已停止")
        except Exception as e:
            print(f"服务器错误: {e}")