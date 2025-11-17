
from gpiozero import OutputDevice
from time import sleep
import os
import sys
import time
# 替换 gpiod 库为 gpiozero 库
from gpiozero import Button 
import hiwonder.ros_robot_controller_sdk as rrc
board = rrc.Board()
st = 0 # 状态变量，用于防止反复响

fanPin1 = OutputDevice(8)
fanPin2 = OutputDevice(7)
# 使用 Button 类初始化引脚 22。Button 默认启用内部上拉电阻，并处理为按下时为 True (低电平触发)。
# 注意：假设这里的 22 对应于 BCM 编号 22。
touch = Button(22)

def set_fan(start):
    if start == 1:
        ## 开启风扇, 顺时针(turn on the fan, clockwise)
        print("Turning fan ON")
        fanPin1.on()  # 等同于输出高电平 (Equivalent to outputting HIGH)
        fanPin2.off() # 等同于输出低电平 (Equivalent to outputting LOW)
    else:
        ## 关闭风扇(turn off the fan)
        print("Turning fan OFF")
        fanPin1.off() # 等同于输出低电平 (Equivalent to outputting LOW)
        fanPin2.off() # 等同于输出低电平 (Equivalent to outputting LOW)
        
if __name__ == '__main__': 
    try:
        while True:
            # 读取传感器状态。touch.is_pressed 在传感器被按下(低电平)时返回 True
            state = touch.is_pressed   
            
            if state: # 如果传感器被按下 (对应原代码 if not state:)
                if st:            # 这里做一个判断，防止反复响
                    st = 0
                    set_fan(1) 
            else: # 如果传感器未被按下 (对应原代码 else:)
                st = 1
                # 关闭蜂鸣器
                set_fan(0)
            
            # 增加一个小的延时，避免 CPU 占用过高
            time.sleep(0.1) 
            
    except KeyboardInterrupt:
        # 捕获键盘中断 (Ctrl+C)
        pass
    finally:
        # 无论如何，确保程序退出时关闭蜂鸣器
        board.set_buzzer(1000, 0.0, 0.0, 1) # 关闭
        print("Program terminated.")