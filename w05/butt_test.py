
import os
import sys
import time
# 替换 gpiod 库为 gpiozero 库
from gpiozero import Button 
import hiwonder.ros_robot_controller_sdk as rrc
board = rrc.Board()
st = 0 # 状态变量，用于防止反复响

# 使用 Button 类初始化引脚 22。Button 默认启用内部上拉电阻，并处理为按下时为 True (低电平触发)。
# 注意：假设这里的 22 对应于 BCM 编号 22。
touch = Button(22)
import time

def play_springlight_shadow(board):
                board.set_buzzer(330, 0.6, 0.9, 1)  # 3
                time.sleep(0.6)
                board.set_buzzer(293, 0.3, 0.9, 1)  # 2
                time.sleep(0.3)
                board.set_buzzer(261, 0.6, 0.9, 1)  # 1
                time.sleep(0.6)
                board.set_buzzer(293, 0.3, 0.9, 1)  # 2
                time.sleep(0.3)
                board.set_buzzer(330, 0.45, 0.9, 1)  # 3.
                time.sleep(0.45)
                board.set_buzzer(349, 0.15, 0.9, 1)  # 4
                time.sleep(0.15)
                board.set_buzzer(330, 0.3, 0.9, 1)  # 3
                time.sleep(0.3)
                board.set_buzzer(293, 0.9, 0.9, 1)  # 2
                time.sleep(0.9)
def haruhikage_play(board):
    board.set_buzzer(261, 0.15, 0.9, 1)  # C5
    time.sleep(0.15)
    board.set_buzzer(293, 0.15, 0.9, 1)  # D5
    time.sleep(0.15)
    board.set_buzzer(330, 0.29, 0.9, 1)  # E5
    time.sleep(0.3)
    board.set_buzzer(330, 0.29, 0.9, 1)  # F5
    time.sleep(0.3)
    board.set_buzzer(293, 0.3, 0.9, 1)  # G5
    time.sleep(0.3)
    board.set_buzzer(349, 0.3, 0.9, 1)  # E5
    time.sleep(0.3)
    board.set_buzzer(330, 0.3, 0.9, 1)  # D5
    time.sleep(0.3)
    board.set_buzzer(293, 0.29, 0.9, 1)  # C5
    time.sleep(0.3)
    board.set_buzzer(293, 0.29, 0.9, 1)  # E5
    time.sleep(0.3)
    board.set_buzzer(293, 0.29, 0.9, 1)  # E5
    time.sleep(0.3)
    board.set_buzzer(261, 0.3, 0.9, 1)  # D5
    time.sleep(0.3)
    board.set_buzzer(349, 0.3, 0.9, 1)  # E5
    time.sleep(0.3)
    board.set_buzzer(330, 0.3, 0.9, 1)  # D5
    time.sleep(0.3)
    board.set_buzzer(293, 0.29, 0.9, 1)  # E5
    time.sleep(0.3)
    board.set_buzzer(293, 0.6, 0.9, 1)  # E5
    time.sleep(0.6)
    board.set_buzzer(261, 0.15, 0.9, 1)  # E5
    time.sleep(0.15)
    board.set_buzzer(293, 0.15, 0.9, 1)  # E5
    time.sleep(0.15)
    board.set_buzzer(330, 0.6, 0.9, 1)  # E5
    time.sleep(0.6)
if __name__ == '__main__': 
    try:
        while True:
            # 读取传感器状态。touch.is_pressed 在传感器被按下(低电平)时返回 True
            state = touch.is_pressed
            if state: # 如果传感器被按下 (对应原代码 if not state:)
                for i in range(3):
                    play_springlight_shadow(board)
                haruhikage_play(board)
            else: # 如果传感器未被按下 (对应原代码 else:)
                # 关闭蜂鸣器
                board.set_buzzer(1000, 0.0, 0.0, 1) 
            
            # 增加一个小的延时，避免 CPU 占用过高
            time.sleep(0.1) 
            
    except KeyboardInterrupt:
        # 捕获键盘中断 (Ctrl+C)
        pass
    finally:
        # 无论如何，确保程序退出时关闭蜂鸣器
        board.set_buzzer(1000, 0.0, 0.0, 1) # 关闭
        print("Program terminated.")