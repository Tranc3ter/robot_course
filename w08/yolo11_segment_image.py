import argparse
import os
import sys
import cv2
from ultralytics import YOLO


def parse_args():
    parser = argparse.ArgumentParser(description="Run YOLOv11 segmentation on a single image")
    parser.add_argument("--input", "-i", default="image.jpg", help="Input image path")
    parser.add_argument("--output", "-o", default="image_segmented.png", help="Output image path")
    parser.add_argument("--model", "-m", default="yolo11n-seg.pt", help="YOLO segmentation model path")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--iou", type=float, default=0.45, help="IOU threshold")
    return parser.parse_args()


def main():
    args = parse_args()

    if not os.path.exists(args.input):
        print(f"输入文件不存在: {args.input}")
        sys.exit(1)

    if not os.path.exists(args.model):
        print(f"模型文件未找到: {args.model}")
        print("请将模型放在当前目录或通过 --model 指定模型路径。")
        sys.exit(1)

    print(f"加载模型: {args.model}")
    try:
        model = YOLO(args.model)
    except Exception as e:
        print(f"模型加载失败: {e}")
        sys.exit(1)

    print(f"处理图像: {args.input}")
    try:
        results = model(args.input, conf=args.conf, iou=args.iou, verbose=False)
    except Exception as e:
        print(f"推理失败: {e}")
        sys.exit(1)

    if len(results) > 0:
        try:
            output_img = results[0].plot()
        except Exception as e:
            print(f"生成可视化失败，回退为原图: {e}")
            output_img = cv2.imread(args.input)
    else:
        print("未检测到任何目标，保存原图。")
        output_img = cv2.imread(args.input)

    if output_img is None:
        print("无法读取或生成输出图像")
        sys.exit(1)

    ok = cv2.imwrite(args.output, output_img)
    if ok:
        print(f"已保存输出: {args.output}")
    else:
        print(f"保存输出失败: {args.output}")


if __name__ == "__main__":
    main()
