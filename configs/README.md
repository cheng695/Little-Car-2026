# Robot Config

这个目录存放机器人配置文件。当前主配置文件是：

```text
little_car_2026.yaml
```

STM32 固件运行时不会解析 YAML。配置文件需要先通过脚本生成 C++ 头文件，然后工程再编译这些生成文件。

```powershell
python Car-whc\User\src\Tools\script\yaml_to_config.py
```

生成文件在：

```text
Car-whc/User/src/Tools/generated/robot_config.hpp
Car-whc/User/src/Tools/generated/robot_messages.hpp
Car-whc/User/src/Tools/generated/robot_runtime.hpp
```

## 顶层结构

当前配置主要分成这些部分：

```yaml
robot:
geometry:
communication:
messages:
control:
hardware:
```

`robot_config.hpp` 主要保存静态配置，例如机器人名称、PID 参数、电机映射、编码器映射、串口映射。

`robot_messages.hpp` 生成消息结构体和发布/订阅函数。

`robot_runtime.hpp` 生成运行时实例，例如 PID、IK、电机、PWM、编码器。

## robot

```yaml
robot:
  name: LittleCar2026
  target: default_car
  chassis_type: differential_drive
```

字段说明：

- `name`: 机器人名称。
- `target`: 当前配置目标名。
- `chassis_type`: 底盘类型，目前脚本只支持 `differential_drive`。

## geometry

```yaml
geometry:
  chassis:
    wheel_radius_m: 0.022
    track_width_m: 0.13
    half_track_m: 0.065
```

这里记录底盘几何参数，主要用于说明和统一配置。当前 IK 生成实际读取的是 `control.chassis_ik.config` 里的参数。

## messages

`messages` 用来生成消息结构体、发布函数和订阅函数。

普通字段写法：

```yaml
RemoteData:
  publisher: RemoteDriver
  fields:
    target_forward: float
    target_rotation: float
  subscribers:
    - Chassis_RemoteData
```

会生成：

```cpp
struct RemoteData
{
    float target_forward = {};
    float target_rotation = {};
};

PublishRemoteData(msg);
SubscribeRemoteData(callback);
```

数组字段写法：

```yaml
MotorFeedback:
  publisher: MotorDriver
  fields:
    motors:
      count: 4
      fields:
        speed_rads: float
        speed_rpm: float
        angle_rad: float
        angle_deg: float
  subscribers:
    - Chassis_MotorFeedback
```

会生成：

```cpp
struct MotorFeedback
{
    struct MotorsItem
    {
        float speed_rads = {};
        float speed_rpm = {};
        float angle_rad = {};
        float angle_deg = {};
    };
    MotorsItem motors[4] = {};
};
```

使用方式：

```cpp
RobotMessages::MotorFeedback msg{};
msg.motors[i].speed_rads = speed;
PublishMotorFeedback(msg);
```

消息字段目前支持：

```text
bool
float
double
int8_t / uint8_t
int16_t / uint16_t
int32_t / uint32_t
int64_t / uint64_t
```

`subscribers` 目前最多 4 个。

## control.chassis_ik

```yaml
control:
  chassis_ik:
    type: differential_drive
    config:
      wheel_radius_m: 0.022
      half_track_m: 0.065
```

会生成：

```cpp
RobotConfig::kChassisIKConfig
RobotRuntime::ChassisIK()
```

使用方式：

```cpp
ChassisIK().DiffInvKinematics(target_forward, target_rotation);
float target_speed = ChassisIK().GetMotor_wheel(i);
```

轮子顺序约定为：

```text
0: left_front
1: right_front
2: left_back
3: right_back
```

## control.pid

未写 `array: true` 的普通 PID 配置：

```yaml
chassis_left_front_speed:
  kp: 1.2
  ki: 0.05
  kd: 0.01
  output_limit: 1000
  integral_limit: 1000
  integral_separation_threshold: 100.0
  R: 50.0
  T: 0.001
```

会生成单个实例函数：

```cpp
RobotConfig::kPidChassisLeftFrontSpeed
RobotRuntime::ChassisLeftFrontSpeedPid()
```

如果这个 PID 是四个轮子同类控制器的一员，可以加：

```yaml
array: true
array_name: chassis_speed
array_index: 0
```

例如四个轮速 PID 都写了 `array: true` 后，会额外生成：

```cpp
RobotRuntime::ChassisSpeedPids()[4]
```

数组名由 `array_name` 生成，`chassis_speed` 会生成 `ChassisSpeedPids()`。

`array_index` 表示当前 PID 在数组里的下标。比如：

```yaml
chassis_left_front_speed:
  array: true
  array_name: chassis_speed
  array_index: 0

chassis_right_front_speed:
  array: true
  array_name: chassis_speed
  array_index: 1
```

会生成：

```cpp
ChassisSpeedPids()[0]
ChassisSpeedPids()[1]
```

如果以后要加第二组 PID 数组，例如角度环，可以写：

```yaml
chassis_left_front_angle:
  array: true
  array_name: chassis_angle
  array_index: 0
```

会生成另一个数组：

```cpp
ChassisAnglePids()
```

写了 `array: true` 的 PID 不再生成单个实例函数，只通过数组访问。没写 `array: true` 的 PID 会生成单个实例函数。

同一个 `array_name` 里的 `array_index` 必须从 0 开始连续，不能重复，不能跳号。

## hardware.motors

电机配置示例：

```yaml
left_front:
  array: true
  array_name: chassis
  array_index: 0
  interface: M1
  ik_index: 0
  side: left
  position: front
  reduction_ratio: 20.0
  pwm_a: { timer: htim1, channel: TIM_CHANNEL_3, gpio: PE13 }
  pwm_b: { timer: htim1, channel: TIM_CHANNEL_4, gpio: PE14 }
  encoder: left_front_encoder
  speed_pid: chassis_left_front_speed
  reverse: true
```

字段说明：

- `interface`: 板子上的接口名，例如 `M1`。
- `array`: 是否把这一组底盘电机的 PWM 运行时实例生成数组入口。
- `array_name`: 数组组名，例如 `chassis` 会生成 `ChassisPwmA()` 和 `ChassisPwmB()`。
- `array_index`: 当前电机在数组里的下标。
- `ik_index`: 底盘 IK 和数组使用的轮子下标，必须是 `0..3`。
- `side`: 左右侧标记。
- `position`: 前后位置标记。
- `reduction_ratio`: 减速比。
- `pwm_a`: 电机驱动 A 输入 PWM 通道。
- `pwm_b`: 电机驱动 B 输入 PWM 通道。
- `encoder`: 绑定的编码器配置名。
- `speed_pid`: 绑定的速度 PID 配置名。
- `reverse`: 方向是否反向，目前会进入静态配置，是否生效取决于电机库是否使用该字段。

脚本要求四个电机必须刚好定义 `ik_index` 为 `0, 1, 2, 3`，且不能重复。

生成的运行时入口：

```cpp
ChassisPwmA()[4]
ChassisPwmB()[4]
ChassisMotorConfigs()[4]
ChassisMotors()
```

如果电机写了 `array: true`，脚本会按 `array_name` 生成 PWM 数组。比如 `array_name: chassis` 会生成 `ChassisPwmA()[4]` 和 `ChassisPwmB()[4]`，不会再生成 `LeftFrontPwmA()` 这类单个包装函数。

如果四个电机都没写 `array: true`，脚本会生成单个入口，例如：

```cpp
LeftFrontPwmA()
LeftFrontPwmB()
RightFrontPwmA()
RightFrontPwmB()
```

同一个 `array_name` 里的 `array_index` 必须从 0 开始连续，不能重复，不能跳号。

`ChassisMotors()` 返回的是一个管理四个电机的对象，不是数组。读取第 `i` 个轮子的反馈时，电机库公开接口使用 `1..4` 的电机 id：

```cpp
const uint8_t motor_id = i + 1u;
float speed = ChassisMotors().GetVelocityRads(motor_id);
```

## hardware.encoders

编码器配置示例：

```yaml
left_front_encoder:
  array: true
  array_name: chassis
  array_index: 0
  interface: M1
  timer: htim3
  cpr: 1040
```

字段说明：

- `interface`: 对应电机接口名。
- `array`: 是否把这一组底盘编码器运行时实例生成数组入口。
- `array_name`: 数组组名，例如 `chassis` 会生成 `ChassisEncoderHal()` 和 `ChassisEncoderData()`。
- `array_index`: 当前编码器在数组里的下标。
- `timer`: 编码器模式使用的定时器句柄。
- `cpr`: 编码器每圈计数。

生成的运行时入口：

```cpp
ChassisEncoderHal()[4]
ChassisEncoderData()[4]
```

如果四个编码器都没写 `array: true`，脚本会生成单个入口，例如：

```cpp
LeftFrontEncoderData()
RightFrontEncoderData()
LeftBackEncoderData()
RightBackEncoderData()
```

同一个 `array_name` 里的 `array_index` 必须从 0 开始连续，不能重复，不能跳号。

## communication.uart

串口配置示例：

```yaml
debug:
  logical_id: Debug
  handle: huart1
  baudrate: 115200
  tx_mode: dma
  rx_mode: idle_dma
  rx_buffer_size: 44
  rx_callback: Debug_OnUartRx
```

目前脚本会把这些配置写入 `RobotConfig::kUarts[]`，后续可以继续扩展成 UART 运行时实例。

## 推荐数据流

闭环控制建议这样分层：

```text
ControlTask:
  读取反馈 -> 更新本地 motor_data -> PublishMotorFeedback
  IK + PID -> 填充 chassis_output -> PublishChassisOutput

HardwareTask:
  SubscribeChassisOutput
  将 output 转为 duty
  ChassisMotors().SetDuty(...)

其他任务:
  SubscribeMotorFeedback
  用于日志、显示、通信、调试
```

这样电机库只由少数硬件相关任务直接调用，其他任务通过消息拿数据，耦合会低一些。

## 修改配置后的流程

每次修改 `little_car_2026.yaml` 后，按顺序执行：

```powershell
python Car-whc\User\src\Tools\script\yaml_to_config.py
.\build.ps1
```

默认情况下，脚本会根据输入 YAML 所在目录推导输出目录。例如输入文件在：

```text
SomeProject/User/configs/xxx.yaml
```

默认生成到：

```text
SomeProject/User/src/Tools/generated/
```

如果要指定输出位置，可以使用：

```powershell
python yaml_to_config.py -i path\to\config.yaml -o path\to\robot_config.hpp --messages-output path\to\robot_messages.hpp --runtime-output path\to\robot_runtime.hpp
```

如果只改了生成文件，不重新运行脚本，下一次生成时手改内容会被覆盖。因此 `robot_config.hpp`、`robot_messages.hpp`、`robot_runtime.hpp` 应该视为生成文件，优先修改 YAML 和生成脚本。
