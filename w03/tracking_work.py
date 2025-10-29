import argparse
import socket
import struct
import cv2
import numpy as np
import sys


def create_tracker():
    # Prefer CSRT, fall back to KCF or MOSSE if not available
    if hasattr(cv2, "legacy"):
        if hasattr(cv2.legacy, "TrackerCSRT_create"):
            return cv2.legacy.TrackerCSRT_create()
        if hasattr(cv2.legacy, "TrackerKCF_create"):
            return cv2.legacy.TrackerKCF_create()
    else:
        if hasattr(cv2, "TrackerCSRT_create"):
            return cv2.TrackerCSRT_create()
        if hasattr(cv2, "TrackerKCF_create"):
            return cv2.TrackerKCF_create()
    raise RuntimeError("No compatible tracker found. Install opencv-contrib-python.")


def recv_all(sock, length):
    data = b""
    while len(data) < length:
        packet = sock.recv(length - len(data))
        if not packet:
            return None
        data += packet
    return data


def main():
    parser = argparse.ArgumentParser(description="Socket video tracking client")
    parser.add_argument("--host", default="192.168.137.164", help="server host")
    parser.add_argument("--port", default=8888, type=int, help="server port")
    args = parser.parse_args()

    addr = (args.host, args.port)
    print(f"Connecting to {addr}...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(addr)
    except Exception as e:
        print("无法连接到服务器:", e)
        sys.exit(1)

    try:
        # First frame: receive length then full frame
        data_len = sock.recv(4)
        if not data_len:
            print("Server closed connection (no initial length)")
            return
        length = struct.unpack(">I", data_len)[0]
        raw = recv_all(sock, length)
        if raw is None:
            print("Failed to receive initial frame data")
            return

        img_array = np.frombuffer(raw, dtype=np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if frame is None:
            print("解码初始帧失败")
            return

        # Let user select ROI on the first received frame
        print("请在窗口中选择跟踪目标，按 ENTER 或 SPACE 确认，按 c 取消")
        bbox = cv2.selectROI("Select ROI", frame, fromCenter=False, showCrosshair=True)
        cv2.destroyWindow("Select ROI")
        if bbox == (0, 0, 0, 0):
            print("未选择 ROI，退出")
            return

        tracker = create_tracker()
        ok = tracker.init(frame, bbox)
        if not ok:
            print("跟踪器初始化失败")
            return

        cv2.namedWindow("Tracking", cv2.WINDOW_NORMAL)

        while True:
            # receive next frame length
            data_len = sock.recv(4)
            if not data_len:
                print("Server closed connection")
                break
            length = struct.unpack(">I", data_len)[0]

            raw = recv_all(sock, length)
            if raw is None:
                print("Connection lost while receiving frame")
                break

            img_array = np.frombuffer(raw, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if frame is None:
                print("警告：解码帧失败，跳过此帧")
                continue

            ok, bbox = tracker.update(frame)
            if ok:
                x, y, w, h = map(int, bbox)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, "Tracking", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "Lost - press 'r' to reselect", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            (0, 0, 255), 2)

            cv2.imshow("Tracking", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("r"):
                # reselect ROI on current frame
                cv2.imshow("Tracking", frame)
                bbox = cv2.selectROI("Reselect ROI", frame, fromCenter=False, showCrosshair=True)
                cv2.destroyWindow("Reselect ROI")
                if bbox != (0, 0, 0, 0):
                    tracker = create_tracker()
                    tracker.init(frame, bbox)

    finally:
        sock.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()