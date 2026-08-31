import time
import serial  # Install with: pip install pyserial
import Robotic_Arm.rm_ctypes_wrap
from Robotic_Arm import *
from Robotic_Arm.rm_ctypes_wrap import rm_create_robot_arm
from Robotic_Arm.rm_robot_interface import RoboticArm

# ================= Configuration =================
# Set the STM32 serial port (typically COMx on Windows or /dev/ttyUSBx on Linux)
SERIAL_PORT = '/dev/ttyUSB0'  
BAUD_RATE = 115200    # Must match the STM32 firmware baud rate

# Map val from [in_min, in_max] to [out_min, out_max]
def map_value(val, in_min, in_max, out_min, out_max):
    # Avoid division by zero
    if in_max - in_min == 0:
        return out_min
    
    # Compute the linear mapping
    result = (val - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    
    # Clamp the result to 0..65535
    if result < out_min: return out_min
    if result > out_max: return out_max
    return int(result)

def main():
    arm_connected = False
    ser = None
    
    try:
        # 1. Connect to the robot arm
        print("正在连接机械臂...")
        arm = RoboticArm(Robotic_Arm.rm_robot_interface.rm_thread_mode_e.RM_TRIPLE_MODE_E)
        handle = arm.rm_create_robot_arm("192.168.1.19", 8080)
        
        # Check connection status; retain the original handle check for this SDK
        if not arm: 
            print("机械臂连接失败，请检查IP和端口")
            return -1
        
        print(f"机械臂连接成功，ID: {handle}")
        arm_connected = True

        # Set the operating mode
        arm.rm_set_arm_run_mode(1)
        arm.rm_set_arm_max_line_speed(0.05)
        arm.rm_set_hand_speed(1000)
        print("机械臂初始化完成")

        # 2. Connect to the STM32 serial port
        print(f"正在打开串口 {SERIAL_PORT}...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        print("串口连接成功")

        # ================= Calibration =================
        print("\n" + "="*40)
        print("  进入校准模式")
        print("  请在接下来 10 秒内，反复用力 张开 和 握紧 你的手")
        print("  以便程序记录手指的最大和最小活动范围！")
        print("="*40 + "\n")

        for i in range(3, 0, -1):
            print(f"校准倒计时: {i}...")
            time.sleep(1)
        print(">>> 开始记录数据！请活动手指！ <<<")

        # Initialize minimum and maximum bounds to opposite extremes
        min_vals = [9999.0] * 6
        max_vals = [-9999.0] * 6
        
        start_time = time.time()
        # Collect calibration data for 10 seconds
        while time.time() - start_time < 10:
            if ser.in_waiting:
                try:
                    # Read and decode one line
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if not line: continue
                    
                    # Parse CSV data: "v0,v1,v2,..."
                    parts = line.split(',')
                    if len(parts) >= 6:
                        # Extract the first six voltage channels
                        current_volts = [float(x) for x in parts[:6]]
                        
                        # Update the minimum and maximum values
                        for i in range(6):
                            if current_volts[i] < min_vals[i]: min_vals[i] = current_volts[i]
                            if current_volts[i] > max_vals[i]: max_vals[i] = current_volts[i]
                        
                        # Show the first channel calibration status as progress feedback
                        print(f"\r[校准中] Ch0范围: {min_vals[0]:.2f} ~ {max_vals[0]:.2f}V", end="")
                except ValueError:
                    continue

        print("\n\n校准完成！各通道范围如下：")
        for i in range(6):
            print(f"  手指 {i+1}: {min_vals[i]:.2f}V -> {max_vals[i]:.2f}V")
            # Expand an insufficient range to avoid division errors if the hand did not move
            if max_vals[i] - min_vals[i] < 0.1:
                print(f"  [警告] 手指 {i+1} 活动范围过小，已应用默认修正")
                max_vals[i] = min_vals[i] + 1.0

        # ================= Control loop =================
        print("\n" + "="*40)
        print("  进入同步控制模式")
        print("  按 Ctrl+C 停止程序")
        print("="*40 + "\n")
        
        # Clear the serial buffer to start with fresh data
        ser.reset_input_buffer()

        while True:
            if ser.in_waiting:
                try:
                    # Read the latest line
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if not line: continue
                    
                    parts = line.split(',')
                    if len(parts) >= 6:
                        # 1. Read the current voltage
                        volts = [float(x) for x in parts[:6]]
                        
                        # 2. Map to 0..65535
                        target_angles = []
                        for i in range(6):
                            # If bending increases the sensor voltage but should decrease the robot command,
                            # reverse the last two map_value arguments: map_value(..., 65535, 0)
                            mapped = map_value(volts[i], min_vals[i], max_vals[i], 0, 65535)
                            target_angles.append(mapped)
                        
                        # 3. Send the command to the robot arm
                        # The robot expects a list [angle1, ..., angle6]
                        # False selects nonblocking mode: send without waiting for motion completion
                        arm.rm_set_hand_follow_pos(target_angles, False) 
                        
                        # Optional debug output
                        # print(f"\rControl values: {target_angles}", end="")
                        
                except Exception as e:
                    print(f"数据处理错误: {e}")
                    
    except KeyboardInterrupt:
        print("\n用户停止程序")
    except Exception as e:
        print(f"\n发生严重错误: {str(e)}")
    finally:
        # 7. Release resources
        if ser and ser.is_open:
            ser.close()
            print("串口已关闭")
            
        if arm_connected:
            # Use destroy instead of disconnect
            Robotic_Arm.rm_ctypes_wrap.rm_destroy()
            print("已断开机械臂连接")
        print("程序结束")

if __name__ == "__main__":
    main()