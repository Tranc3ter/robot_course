import zmq
import json
import numpy as np
import soundfile as sf
import io
import traceback
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
# 导入Kokoro
try:
    from kokoro import KPipeline
    HAS_KOKORO = True
    print("成功导入Kokoro TTS引擎")
except ImportError as e:
    print(f"警告: 无法导入Kokoro: {e}")
    HAS_KOKORO = False

class TTSServer:
    def __init__(self, port: int = 5556):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://0.0.0.0:{port}")  # 改为0.0.0.0
        
        # 初始化TTS管道
        if HAS_KOKORO:
            try:
                self.pipeline = KPipeline(lang_code='z')
                print(f"TTS Server (使用真实Kokoro) started on port {port}")
            except Exception as e:
                print(f"Kokoro初始化失败: {e}")
                self.pipeline = None
        else:
            self.pipeline = None
            print(f"TTS Server (模拟模式) started on port {port}")
    
    def text_to_speech(self, text: str, voice: str = 'zf_xiaobei') -> bytes:
        """将文本转换为语音，返回WAV字节数据"""
        try:
            if self.pipeline and HAS_KOKORO:
                # 使用真实Kokoro生成音频
                print(f"使用Kokoro合成语音: '{text[:50]}...'")
                
                generator = self.pipeline(text, voice=voice)
                audio_data = None
                
                for i, (gs, ps, audio) in enumerate(generator):
                    audio_data = audio
                    if i == 0:  # 只取第一段
                        break
                
                if audio_data is not None:
                    # 将音频数据保存为WAV字节
                    wav_io = io.BytesIO()
                    sf.write(wav_io, audio_data, 24000, format='WAV')
                    wav_bytes = wav_io.getvalue()
                    print(f"合成成功: {len(wav_bytes)} 字节")
                    return wav_bytes
                else:
                    print("Kokoro未生成音频")
                    return self.generate_fallback_audio(text)
                    
            else:
                # 生成模拟音频
                print(f"模拟合成语音: '{text[:50]}...'")
                return self.generate_fallback_audio(text)
                
        except Exception as e:
            print(f"TTS转换错误: {e}")
            traceback.print_exc()
            return self.generate_fallback_audio(text)
    
    def generate_fallback_audio(self, text: str) -> bytes:
        """生成备用的模拟音频"""
        try:
            # 生成简单的正弦波作为音频
            duration = min(len(text) * 0.1, 5.0)  # 根据文本长度决定时长
            sample_rate = 24000
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            
            # 生成变化的频率
            base_freq = 220  # A3
            freq_variation = np.sin(2 * np.pi * 2 * t) * 50  # 频率变化
            frequency = base_freq + freq_variation
            
            # 生成音频
            audio = 0.3 * np.sin(2 * np.pi * frequency * t)
            
            # 添加淡入淡出
            fade_samples = int(0.05 * sample_rate)
            if fade_samples > 0:
                fade_in = np.linspace(0, 1, fade_samples)
                fade_out = np.linspace(1, 0, fade_samples)
                audio[:fade_samples] *= fade_in
                audio[-fade_samples:] *= fade_out
            
            # 保存为WAV字节
            wav_io = io.BytesIO()
            sf.write(wav_io, audio, sample_rate, format='WAV')
            wav_bytes = wav_io.getvalue()
            
            return wav_bytes
            
        except Exception as e:
            print(f"生成备用音频失败: {e}")
            return b""
    
    def run(self):
        """运行服务器主循环"""
        while True:
            try:
                # 接收文本数据
                message = self.socket.recv_string()
                data = json.loads(message)
                
                text = data.get('text', '')
                voice = data.get('voice', 'zf_xiaobei')
                
                print(f"[TTS] 收到请求: '{text[:50]}...'")
                
                # 生成语音
                audio_bytes = self.text_to_speech(text, voice)
                
                # 发送响应
                if audio_bytes:
                    response = {
                        'audio': audio_bytes.decode('latin-1'),
                        'sample_rate': 24000,
                        'status': 'success'
                    }
                    print(f"[TTS] 发送音频: {len(audio_bytes)} 字节")
                else:
                    response = {
                        'audio': '',
                        'status': 'error',
                        'error': '音频生成失败'
                    }
                
                self.socket.send_json(response)
                
            except Exception as e:
                print(f"TTS服务器错误: {e}")
                error_response = {
                    'audio': '',
                    'status': 'error',
                    'error': str(e)
                }
                self.socket.send_json(error_response)

if __name__ == "__main__":
    server = TTSServer(port=5556)
    server.run()