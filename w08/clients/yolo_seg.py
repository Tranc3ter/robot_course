import cv2
import socket
import struct
import numpy as np
from ultralytics import YOLO
import time

class YOLOSegmentVisualizer:
    def __init__(self, server_ip="192.168.137.54", server_port=8888):
        # 初始化参数
        self.server_ip = server_ip
        self.server_port = server_port
        
        # 初始化模型
        self.model = self.load_model()
        
        # 连接状态
        self.connected = False
        self.client_socket = None
        
        # 显示控制
        self.show_detections = True
        self.show_fps = True
        self.show_info = True
        
        # 性能统计
        self.fps = 0
        self.prev_time = time.time()
        self.frame_count = 0
        
        # 初始化UI
        self.init_ui()
        
    def load_model(self):
        """加载YOLO模型"""
        print("加载YOLOv11分割模型...")
        try:
            model = YOLO('yolo11n-seg.pt')
            print("✓ 模型加载成功")
            return model
        except Exception as e:
            print(f"✗ 模型加载失败: {e}")
            print("请下载模型: from ultralytics import YOLO; YOLO('yolo11n-seg')")
            return None
    
    def init_ui(self):
        """初始化UI窗口"""
        # 创建主窗口
        cv2.namedWindow("YOLOv11 Real-time Segmentation", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("YOLOv11 Real-time Segmentation", 1280, 800)
        
        # 创建控制面板窗口
        cv2.namedWindow("Control Panel", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Control Panel", 400, 200)
        
        print("\n" + "="*50)
        print("YOLOv11 实时分割可视化系统")
        print("="*50)
        print("快捷键:")
        print("  q - 退出程序")
        print("  s - 保存当前帧")
        print("  d - 显示/隐藏检测框")
        print("  f - 显示/隐藏FPS")
        print("  i - 显示/隐藏信息")
        print("  r - 重置统计")
        print("="*50 + "\n")
    
    def connect_server(self):
        
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.server_ip, self.server_port))
        self.connected = True
        print(f"✓ 已连接到服务器 {self.server_ip}:{self.server_port}")
        return True
        
    
    def receive_frame(self):
        """接收一帧图像"""
        try:
            # 接收帧长度
            data_len = self.client_socket.recv(4)
            if not data_len:
                print("服务器断开连接")
                return None

            length = struct.unpack(">I", data_len)[0]

            # 接收图像数据
            data = b""
            while len(data) < length:
                packet = self.client_socket.recv(min(4096, length - len(data)))
                if not packet:
                    return None
                data += packet

            if len(data) < length:
                print("数据接收不完整")
                return None

            # 解码图像
            img_array = np.frombuffer(data, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            return frame
            
        except Exception as e:
            print(f"接收帧错误: {e}")
            return None
    
    def process_frame(self, frame):
        """处理图像帧"""
        if frame is None:
            return None
        
        self.frame_count += 1
        
        # 计算FPS
        current_time = time.time()
        if self.frame_count > 1:
            self.fps = 1.0 / (current_time - self.prev_time)
        self.prev_time = current_time
        
        # 创建副本用于显示
        display_frame = frame.copy()
        
        # 如果开启检测，运行YOLO
        if self.show_detections and self.model:
            try:
                results = self.model(frame, conf=0.25, iou=0.45, verbose=False)
                
                if len(results) > 0:
                    # 获取带标注的图像
                    processed = results[0].plot()
                    
                    # 保持原始图像作为背景，只在上面添加标注
                    if processed.shape == display_frame.shape:
                        display_frame = processed
                    
                    # 获取检测统计
                    detections = len(results[0].boxes) if results[0].boxes is not None else 0
                else:
                    detections = 0
                    
            except Exception as e:
                print(f"推理错误: {e}")
                detections = 0
        else:
            detections = 0
        
        # 添加信息叠加层
        self.add_overlay(display_frame, detections)
        
        return display_frame, detections
    
    def add_overlay(self, frame, detections):
        """在图像上添加信息叠加层"""
        overlay = frame.copy()
        
        # 添加半透明背景
        cv2.rectangle(overlay, (0, 0), (300, 120), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
        
        # 添加状态信息
        y_offset = 30
        line_height = 25
        
        # FPS
        if self.show_fps:
            cv2.putText(frame, f"FPS: {self.fps:.1f}", 
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.7, (0, 255, 0), 2)
            y_offset += line_height
        
        # 帧计数
        cv2.putText(frame, f"Frame: {self.frame_count}", 
                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.7, (255, 255, 255), 2)
        y_offset += line_height
        
        # 检测数量
        if self.show_detections:
            cv2.putText(frame, f"Detections: {detections}", 
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.7, (0, 200, 255), 2)
            y_offset += line_height
        
        # 状态指示
        status = "ON" if self.show_detections else "OFF"
        cv2.putText(frame, f"YOLO: {status}", 
                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.7, (0, 255, 255) if self.show_detections else (200, 200, 200), 2)
        
        # 添加底部帮助文本
        help_text = "q:Quit  s:Save  d:Detect  f:FPS  i:Info  r:Reset"
        cv2.putText(frame, help_text,
                   (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,
                   0.5, (200, 200, 200), 1)
    
    def create_control_panel(self):
        """创建控制面板图像"""
        panel = np.ones((200, 400, 3), dtype=np.uint8) * 50
        
        # 标题
        cv2.putText(panel, "Control Panel", (20, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # 状态信息
        y_offset = 60
        cv2.putText(panel, f"Connected: {'Yes' if self.connected else 'No'}", 
                   (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                   (0, 255, 0) if self.connected else (0, 0, 255), 2)
        y_offset += 30
        
        cv2.putText(panel, f"Frames: {self.frame_count}", 
                   (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        y_offset += 30
        
        cv2.putText(panel, f"FPS: {self.fps:.1f}", 
                   (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        y_offset += 30
        
        # 控制状态
        cv2.putText(panel, f"Detections: {'ON' if self.show_detections else 'OFF'}", 
                   (200, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                   (0, 255, 0) if self.show_detections else (200, 200, 200), 2)
        
        return panel
    
    def run(self):
        """主运行循环"""
        # 连接服务器
        if not self.connect_server():
            print("无法连接到服务器，程序退出")
            return
        
        print("开始接收视频流...")
        
        try:
            while True:
                # 接收原始帧
                raw_frame = self.receive_frame()
                if raw_frame is None:
                    print("视频流中断")
                    break
                
                # 处理帧
                processed_frame, detections = self.process_frame(raw_frame)
                
                if processed_frame is not None:
                    # 显示主窗口
                    cv2.imshow("YOLOv11 Real-time Segmentation", processed_frame)
                    
                    # 显示控制面板
                    control_panel = self.create_control_panel()
                    cv2.imshow("Control Panel", control_panel)
                
                # 按键处理
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("用户退出")
                    break
                elif key == ord('s'):
                    # 保存当前帧
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    filename = f"segmentation_{timestamp}.jpg"
                    cv2.imwrite(filename, processed_frame)
                    print(f"✓ 已保存: {filename}")
                elif key == ord('d'):
                    self.show_detections = not self.show_detections
                    status = "ON" if self.show_detections else "OFF"
                    print(f"检测模式: {status}")
                elif key == ord('f'):
                    self.show_fps = not self.show_fps
                    status = "显示" if self.show_fps else "隐藏"
                    print(f"FPS显示: {status}")
                elif key == ord('i'):
                    self.show_info = not self.show_info
                    status = "显示" if self.show_info else "隐藏"
                    print(f"信息显示: {status}")
                elif key == ord('r'):
                    self.frame_count = 0
                    print("统计已重置")
                    
        except KeyboardInterrupt:
            print("\n用户中断")
        except Exception as e:
            print(f"运行时错误: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """清理资源"""
        if self.client_socket:
            self.client_socket.close()
        cv2.destroyAllWindows()
        print("程序结束")

# 主程序
if __name__ == "__main__":
    # 创建并运行可视化器
    print("启动YOLOv11实时分割可视化客户端...")
    visualizer = YOLOSegmentVisualizer()
    visualizer.run()