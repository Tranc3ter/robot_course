# yolo_seg_simple.py
import sys
import traceback

def main():
    print("=" * 60)
    print("YOLOv11 实时分割客户端 - 启动")
    print("=" * 60)
    
    try:
        # 1. 导入库
        print("1. 导入库...")
        import cv2
        import socket
        import struct
        import numpy as np
        import time
        print("   ✓ 基础库导入成功")
        
        # 2. 尝试导入YOLO
        print("2. 导入YOLO...")
        try:
            from ultralytics import YOLO
            print("   ✓ ultralytics 导入成功")
        except ImportError as e:
            print(f"   ✗ ultralytics 导入失败: {e}")
            print("   请安装: pip install ultralytics")
            input("按Enter退出...")
            return
        
        # 3. 连接服务器
        print("3. 连接服务器...")
        SERVER_IP = "192.168.137.54"
        SERVER_PORT = 8888
        
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5)
            print(f"   尝试连接 {SERVER_IP}:{SERVER_PORT}...")
            client_socket.connect((SERVER_IP, SERVER_PORT))
            client_socket.settimeout(None)
            print("   ✓ 连接成功！")
        except Exception as e:
            print(f"   ✗ 连接失败: {e}")
            print("\n可能的原因：")
            print(f"   • 服务器IP错误: {SERVER_IP}")
            print(f"   • 服务器端口错误: {SERVER_PORT}")
            print("   • 服务器程序没有运行")
            print("   • 防火墙阻止了连接")
            input("按Enter退出...")
            return
        
        # 4. 加载YOLO模型
        print("4. 加载YOLO模型...")
        try:
            model = YOLO('yolo11n-seg.pt')
            print("   ✓ 模型加载成功")
        except Exception as e:
            print(f"   ✗ 模型加载失败: {e}")
            print("   请确保 yolo11n-seg.pt 文件在当前目录")
            print("   或运行: from ultralytics import YOLO; YOLO('yolo11n-seg') 来自动下载")
            client_socket.close()
            input("按Enter退出...")
            return
        
        # 5. 开始主循环
        print("\n" + "=" * 60)
        print("开始接收和处理视频流...")
        print("按 'q' 退出程序")
        print("按 's' 保存当前帧")
        print("=" * 60 + "\n")
        
        frame_count = 0
        fps = 0
        prev_time = time.time()
        
        cv2.namedWindow("YOLOv11 Segmentation", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("YOLOv11 Segmentation", 800, 600)
        
        while True:
            frame_count += 1
            
            # 接收帧
            try:
                # 接收长度
                data_len = client_socket.recv(4)
                if not data_len:
                    print("服务器断开连接")
                    break
                
                length = struct.unpack(">I", data_len)[0]
                
                # 接收数据
                data = b""
                while len(data) < length:
                    chunk = client_socket.recv(min(4096, length - len(data)))
                    if not chunk:
                        break
                    data += chunk
                
                # 解码
                img_array = np.frombuffer(data, dtype=np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                
                if frame is None:
                    print(f"第 {frame_count} 帧解码失败")
                    continue
                    
            except Exception as e:
                print(f"接收帧错误: {e}")
                break
            
            # YOLO处理
            try:
                results = model(frame, conf=0.25, verbose=False)
                processed_frame = results[0].plot()
                
                # 计算FPS
                current_time = time.time()
                if frame_count > 1:
                    fps = 1.0 / (current_time - prev_time)
                prev_time = current_time
                
                # 添加信息
                cv2.putText(processed_frame, f"FPS: {fps:.1f}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(processed_frame, f"Frame: {frame_count}", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # 显示
                cv2.imshow("YOLOv11 Segmentation", processed_frame)
                
                # 按键处理
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("用户退出")
                    break
                elif key == ord('s'):
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    filename = f"yolo_result_{timestamp}.jpg"
                    cv2.imwrite(filename, processed_frame)
                    print(f"已保存: {filename}")
                    
            except Exception as e:
                print(f"处理帧错误: {e}")
                # 显示原始帧
                cv2.imshow("YOLOv11 Segmentation", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
        
        # 清理
        client_socket.close()
        cv2.destroyAllWindows()
        print("程序正常结束")
        
    except Exception as e:
        print(f"\n发生未捕获的错误: {e}")
        print("错误详情:")
        traceback.print_exc()
        input("按Enter退出...")

if __name__ == "__main__":
    # 确保程序不会静默退出
    try:
        main()
    except Exception as e:
        print(f"致命错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 在Windows下，程序执行完后会立即关闭窗口
    # 添加input来保持窗口打开
    input("程序执行完毕，按Enter键退出...")