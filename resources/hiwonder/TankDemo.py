import smbus
import time
import struct

# 设置I2C总线号，通常为1(Set the I2C bus number, usually 1)
I2C_BUS = 1

# 设置四路电机驱动模块的I2C地址(Set the I2C address of the 4-ch encoder motor driver)
MOTOR_ADDR = 0x34 

# 寄存器地址(Register address)
ADC_BAT_ADDR = 0x00
MOTOR_TYPE_ADDR = 0x14 #编码电机类型设置(Set the encoder motor type)
MOTOR_ENCODER_POLARITY_ADDR = 0x15 #设置编码方向极性(Set the polarity of the encoder)，
#如果发现电机转速根本不受控制，要么最快速度转动，要么停止。可以将此地址的值重新设置一下(If the motor speed can not be controlled, either rotating at the fastest speed or stopping, the value of this address can be reset)
#范围0或1，默认0(Range: 0 or 1, default: 0)
MOTOR_FIXED_PWM_ADDR = 0x1F #固定PWM控制，属于开环控制,范围（-100~100）(Fixed PWM control, open-loop control, range: (-100~100))  
MOTOR_FIXED_SPEED_ADDR = 0x33 #固定转速控制，属于闭环控制(Fixed speed control, closed-loop control,)，
#单位：脉冲数每10毫秒，范围（根据具体的编码电机来，受编码线数，电压大小，负载大小等影响，一般在±50左右）(Unit: pulse count per 10 milliseconds, range: (depending on the specific encoder motor, affected by the number of encoder wires, voltage, load, etc., generally around ±50))

MOTOR_ENCODER_TOTAL_ADDR = 0x3C #4个编码电机各自的总脉冲值(Total pulse value of each of the four encoder motors)
# #如果已知电机每转一圈的脉冲数为U，又已知轮子的直径D，那么就可以通过脉冲计数的方式得知每个轮子行进的距离(If the number of pulses per revolution of the motor is known as U, and the diameter of the wheel is known as D, the distance traveled by each wheel can be obtained by counting the pulses)
# #比如读到电机1的脉冲总数为P，那么行进的距离为(P/U) * (3.14159*D)(For example, if the total number of pulses for motor 1 is P, the distance traveled is (P/U) * (3.14159*D))
# #对于不同的电机可以自行测试每圈的脉冲数U，可以手动旋转10圈读出脉冲数，然后取平均值得出(The number of pulses per revolution U for different motors can be tested manually by rotating 10 revolutions and reading the pulse count, and then taking the average value to obtain)


#电机类型具体值(Motor type values)
MOTOR_TYPE_WITHOUT_ENCODER = 0
MOTOR_TYPE_TT = 1
MOTOR_TYPE_N20 = 2
MOTOR_TYPE_JGB37_520_12V_110RPM = 3 #磁环每转是44个脉冲   减速比:90  默认(Magnetic ring rotates 44 pulses per revolution, reduction ratio: 90, default)

#电机类型及编码方向极性(Motor type and encoder direction polarity)
MotorType = MOTOR_TYPE_JGB37_520_12V_110RPM
MotorEncoderPolarity = 0

bus = smbus.SMBus(I2C_BUS)
speed1 = [50,50,50,50]
speed2 = [-50,-50,-50,-50]
speed3 = [0,0,0,0]

pwm1 = [50,50,50,50]
pwm2 = [-100,-100,-100,-100]
pwm3 = [0,0,0,0]

def Motor_Init(): #电机初始化(initialize motor)
    bus.write_byte_data(MOTOR_ADDR, MOTOR_TYPE_ADDR, MotorType)  #设置电机类型(Set the motor type)
    time.sleep(0.5)
    bus.write_byte_data(MOTOR_ADDR, MOTOR_ENCODER_POLARITY_ADDR, MotorEncoderPolarity)  #设置编码极性(Set the polarity of the encoder)

def main():
    while True:
      battery = bus.read_i2c_block_data(MOTOR_ADDR, ADC_BAT_ADDR)
      print("V = {0}mV".format(battery[0]+(battery[1]<<8)))
      
      Encode = struct.unpack('iiii',bytes(bus.read_i2c_block_data(MOTOR_ADDR, MOTOR_ENCODER_TOTAL_ADDR,16)))
      
      print("Encode1 = {0}  Encode2 = {1}  Encode3 = {2}  Encode4 = {3}".format(Encode[0],Encode[1],Encode[2],Encode[3]))
      
      #PWM控制（注意：PWM控制是一个持续控制的过程，若有延时则会打断电机的运行）(PWM control (Note: PWM control is a continuous control process, and if there is a delay, it will interrupt the motor operation))
      #bus.write_i2c_block_data(MOTOR_ADDR, MOTOR_FIXED_PWM_ADDR,pwm1)
      
      
      #固定转速控制(Fixed rotation speed control)
      bus.write_i2c_block_data(MOTOR_ADDR, MOTOR_FIXED_SPEED_ADDR,speed1)
      time.sleep(3)
      bus.write_i2c_block_data(MOTOR_ADDR, MOTOR_FIXED_SPEED_ADDR,speed2)
      time.sleep(3)
      


if __name__ == "__main__":
    Motor_Init()
    main()
