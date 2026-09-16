#include <Wire.h>

#define I2C_ADDR        0x34

#define ADC_BAT_ADDR                  0
#define MOTOR_TYPE_ADDR               20 //编码电机类型设置(Set encoder motor type)
#define MOTOR_ENCODER_POLARITY_ADDR   21 //设置编码方向极性(Set the encoder direction polarity)，
//如果发现电机转速根本不受控制，要么最快速度转动，要么停止。可以将此地址的值重新设置一下(If the motor speed is completely uncontrollable, either rotating at the fastest speed or stopping. You can reset the value of this address)
//范围0或1，默认0(Range 0 or 1, default 0)
#define MOTOR_FIXED_PWM_ADDR      31 //固定PWM控制，属于开环控制,范围（-100~100）(Fixed PWM control, belongs to open-loop control, range from -100 to 100)
//#define SERVOS_ADDR_CMD 40        
#define MOTOR_FIXED_SPEED_ADDR    51 //固定转速控制，属于闭环控制(Fixed speed control, belongs to closed-loop control)，
//单位：脉冲数每10毫秒，范围（根据具体的编码电机来，受编码线数，电压大小，负载大小等影响，一般在±50左右）(Unit: pulse count per 10 milliseconds, range (depending on the specific encoder motor, affected by the number of encoder lines, voltage size, load size, etc., generally around ±50))

#define MOTOR_ENCODER_TOTAL_ADDR  60 //4个编码电机各自的总脉冲值(Total pulse value of each of the four encoder motors)
//如果已知电机每转一圈的脉冲数为U，又已知轮子的直径D，那么就可以通过脉冲计数的方式得知每个轮子行进的距离(If the pulse count per revolution of the motor is known to be U, and the diameter of the wheel D is known, then the distance traveled by each wheel can be obtained through pulse counting)
//比如读到电机1的脉冲总数为P，那么行进的距离为(P/U) * (3.14159*D)(For example, if the total pulse count of motor 1 is P, then the distance traveled is (P/U) * (3.14159*D))
//对于不同的电机可以自行测试每圈的脉冲数U，可以手动旋转10圈读出脉冲数，然后取平均值得出(For different motors, you can test the number of pulses per revolution U by manually rotating 10 times and reading the pulse count, and then take the average value to obtain it)


//电机类型具体值(motor type specific values)
#define MOTOR_TYPE_WITHOUT_ENCODER        0
#define MOTOR_TYPE_TT                     1
#define MOTOR_TYPE_N20                    2
#define MOTOR_TYPE_JGB                    3  //磁环每转是44个脉冲   减速比:131  默认(Magnetic ring rotates 44 pulses per revolution, reduction ratio: 131, default)

u8 data[20];
bool WireWriteByte(uint8_t val)
{
    Wire.beginTransmission(I2C_ADDR);
    Wire.write(val);
    if( Wire.endTransmission() != 0 ) {
        return false;
    }
    return true;
}
bool WireWriteDataArray(  uint8_t reg,uint8_t *val,unsigned int len)
{
    unsigned int i;

    Wire.beginTransmission(I2C_ADDR);
    Wire.write(reg);
    for(i = 0; i < len; i++) {
        Wire.write(val[i]);
    }
    if( Wire.endTransmission() != 0 ) {
        return false;
    }

    return true;
}
bool WireReadDataByte(uint8_t reg, uint8_t &val)
{
    if (!WireWriteByte(reg)) {
        return false;
    }
    
    Wire.requestFrom(I2C_ADDR, 1);
    while (Wire.available()) {
        val = Wire.read();
    }
    
    return true;
}
int WireReadDataArray( uint8_t reg, uint8_t *val, unsigned int len)
{
    unsigned char i = 0;
    
    /* Indicate which register we want to read from */
    if (!WireWriteByte(reg)) {
        return -1;
    }
    
    /* Read block data */
    Wire.requestFrom(I2C_ADDR, len);
    while (Wire.available()) {
        if (i >= len) {
            return -1;
        }
        val[i] = Wire.read();
        i++;
    }
    
    return i;
}


uint8_t MotorType = MOTOR_TYPE_JGB;
uint8_t MotorEncoderPolarity = 0; 

void setup()
{
  
  Wire.begin();
  delay(200);
  WireWriteDataArray(MOTOR_TYPE_ADDR,&MotorType,1);
  delay(5);
  WireWriteDataArray(MOTOR_ENCODER_POLARITY_ADDR,&MotorEncoderPolarity,1);
  delay(2000);
}

int8_t car_forward[4]={30,-30,-30,30};                  // 前进(forward)
int8_t car_back[4]={-30,30,30,-30};                     // 后退(backward)

int8_t car_left_transform[4]={-30,-30,-30,-30};         // 左平移(move horizontally to the left)
int8_t car_right_transform[4]={30,30,30,30};            // 右平移(move horizontally to the right)


int8_t car_turn_left[4]={30,-30,-10,10};                // 向左转(turn left)
int8_t car_turn_right[4]={10,-10,-30,30};               // 向右转(turn right)

int8_t car_turn_left_back[4]={-30,30,10,-10};           // 左倒退(left reverse)
int8_t car_turn_right_back[4]={-10,10,30,-30};          // 右倒退(right reverse)

int8_t car_turn_right_orin[4]={-30,30,-30,30};          // 原地左转(turn left in place)
int8_t car_turn_left_orin[4]={30,-30,30,-30};           // 原地右转(turn right in place)

int8_t car_Ob_translation_left_up[4]={0,-30,-30,0};     // 左前平移(move horizontally to the left front)
int8_t car_Ob_translation_right_up[4]={30,0,0,30};      // 右前平移(move horizontally to the right front)

int8_t car_Ob_translation_left_back[4]={-30,0,0,-30};   // 左后平移(move horizontally to the left rear)
int8_t car_Ob_translation_right_back[4]={0,30,30,0};    // 右后平移(move horizontally to the right rear)

int8_t car_drift_left[4]={-30,0,-30,0};                 // 左漂移(drift left)
int8_t car_drift_right[4]={30,0,30,0};                  // 右漂移(drift right)

int8_t car_stop[4]={0,0,0,0};                           // 停止(stop)


void Running(int8_t running_mode[4])
{
  WireWriteDataArray(MOTOR_FIXED_SPEED_ADDR,running_mode,4);  //执行对应动作(execute corresponding action)
  delay(2000);
  WireWriteDataArray(MOTOR_FIXED_SPEED_ADDR,car_stop,4);      // 停止(stop)
  delay(1000);
}
  
void loop()
{

    Running(car_forward);                   // 前进(forward)
    Running(car_back);                      // 向后退(backward)
    Running(car_left_transform);            // 左平移(move horizontally to the left)
    Running(car_right_transform);           // 右平移(move horizontally to the right)
    Running(car_turn_left_orin);            // 原地左转(turn left in place)
    Running(car_turn_right_orin);           // 原地右转(turn right in place)
    Running(car_Ob_translation_left_up);    // 左前平移(move horizontally to the left front)
    Running(car_Ob_translation_right_back); // 右后平移(move horizontally to the right rear)
    Running(car_drift_left);                // 左漂移(drift left)
    Running(car_drift_right);               // 右漂移(drift right)
    while(1){}
}
