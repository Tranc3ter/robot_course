
import cv2
import numpy as np
import socket
import struct
import time
import argparse
from ultralytics import YOLO

def recv_all(sock, length):
    data = b""
    while len(data) < length:
        packet = sock.recv(length - len(data))
        if not packet:
            return None
        data += packet
    return data


def get_frame(ip="localhost", port=8888, timeout=10):
    client_socket = None
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(timeout)
        print(f"尝试连接到服务器 {ip}:{port}...")
        client_socket.connect((ip, port))
        print("成功连接到视频流服务器")

        while True:
            # 读取 4 字节长度（大端）
            data_len = client_socket.recv(4)
            if not data_len:
                # 连接关闭
                break
            try:
                length = struct.unpack('>I', data_len)[0]
            except struct.error as e:
                print(f"无法解析帧长度: {e}")
                break

            # 接收完整帧数据
            raw = recv_all(client_socket, length)
            if raw is None:
                print("连接丢失：未能接收完整帧")
                break

            # 将接收到的字节解码为图像
            img_array = np.frombuffer(raw, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if frame is None:
                print("警告：解码帧失败，跳过此帧")
                continue

            yield frame

    except Exception as e:
        print(f"连接视频流服务器失败: {e}")
        print("请确保视频流服务器正在运行")
    finally:
        if client_socket:
            client_socket.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLO client for length-prefixed frame server")
    parser.add_argument("--host", default="192.168.137.164", help="video server host (default matches tracking_work.py)")
    parser.add_argument("--port", type=int, default=8888, help="video server port")
    parser.add_argument("--model", default="yolo11n.pt", help="path to YOLO model")
    parser.add_argument("--device", default="cuda", help="device to run model on, e.g. 'cuda' or 'cpu'")
    parser.add_argument("--conf", type=float, default=0.5, help="confidence threshold")
    args = parser.parse_args()

    # Load model
    model = YOLO(args.model)
    # Try to move to requested device, fall back gracefully
    try:
        model.to(args.device)
        print(f"模型已加载到设备: {args.device}")
    except Exception as e:
        print(f"无法将模型移动到 {args.device}，将使用 CPU。原因: {e}")
        try:
            model.to("cpu")
        except Exception:
            pass

    # Connect to server specified by args
    for frame in get_frame(ip=args.host, port=args.port):
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
        # Run inference
        try:
            results = model(frame, stream=True, conf=args.conf)
        except Exception as e:
            print(f"模型推理失败: {e}")
            continue

        for result in results:
            annotated_frame = result.plot()
            cv2.imshow("YOLO11 Detection", annotated_frame)