# configs

本目录用于存放整车配置源文件。STM32 固件运行时不直接解析 YAML，推荐后续由脚本读取 YAML，并生成 C/C++ 配置代码，例如：

- `robot_config.hpp`
- `pid_config.cpp`
- `bsp_motor_config.cpp`
- `drv_uart_map.cpp`
- `message_bindings.cpp`

配置文件的目标是把“车是什么样、硬件接在哪里、控制参数是多少”写清楚。新车可以直接复制下面模板，再按实际硬件改值。

## 生成配置

转换脚本位于：

```text
src/Tools/script/yaml_to_config.py
```

默认输入：

```text
configs/little_car_2026.yaml
```

默认输出：

```text
src/Tools/generated/robot_config.hpp
```

运行：

```bash
python src/Tools/script/yaml_to_config.py
```

指定输入和输出：

```bash
python src/Tools/script/yaml_to_config.py \
  --input configs/little_car_2026.yaml \
  --output src/Tools/generated/robot_config.hpp
```

脚本会检查：

- `chassis_type` 和 `chassis_ik.type` 是否为 `differential_drive`
- 四个电机是否完整定义 `ik_index: 0..3`
- 电机引用的 `encoder` 是否存在
- 电机引用的 `speed_pid` 是否存在
- PID 是否包含 `kp/ki/kd/output_limit/integral_limit/T`

## 完整模板

```yaml
robot:
  name: LittleCar2026
  target: default_car
  chassis_type: differential_drive

geometry:
  chassis:
    wheel_radius_m: 0.022
    track_width_m: 0.13
    half_track_m: 0.065

communication:
  uart:
    debug:
      logical_id: Debug
      handle: huart1
      baudrate: 115200
      tx_mode: dma
      rx_mode: idle_dma
      rx_buffer_size: 64
      rx_callback: Debug_OnUartRx

messages:
  RemoteData:
    publisher: RemoteDriver
    subscribers:
      - Chassis_RemoteData

  MotorFeedback:
    publisher: MotorDriver
    subscribers:
      - Chassis_MotorFeedback

control:
  chassis_ik:
    type: differential_drive
    config:
      wheel_radius_m: 0.022
      half_track_m: 0.065

  pid:
    chassis_left_front_speed:
      kp: 1.2
      ki: 0.05
      kd: 0.01
      output_limit: 1000
      integral_limit: 1000
      integral_separation_threshold: 100.0
      R: 50.0
      T: 0.001

    chassis_right_front_speed:
      kp: 1.2
      ki: 0.05
      kd: 0.01
      output_limit: 1000
      integral_limit: 1000
      integral_separation_threshold: 100.0
      R: 50.0
      T: 0.001

    chassis_left_back_speed:
      kp: 1.2
      ki: 0.05
      kd: 0.01
      output_limit: 1000
      integral_limit: 1000
      integral_separation_threshold: 100.0
      R: 50.0
      T: 0.001

    chassis_right_back_speed:
      kp: 1.2
      ki: 0.05
      kd: 0.01
      output_limit: 1000
      integral_limit: 1000
      integral_separation_threshold: 100.0
      R: 50.0
      T: 0.001

hardware:
  motors:
    left_front:
      interface: M1
      ik_index: 0
      side: left
      position: front
      pwm_a: { timer: htim1, channel: TIM_CHANNEL_3, gpio: PE13 }
      pwm_b: { timer: htim1, channel: TIM_CHANNEL_4, gpio: PE14 }
      encoder: left_front_encoder
      speed_pid: chassis_left_front_speed
      reverse: true

    right_front:
      interface: M3
      ik_index: 1
      side: right
      position: front
      pwm_a: { timer: htim8, channel: TIM_CHANNEL_1, gpio: PA5, complementary: true }
      pwm_b: { timer: htim8, channel: TIM_CHANNEL_2, gpio: PB0, complementary: true }
      encoder: right_front_encoder
      speed_pid: chassis_right_front_speed
      reverse: false

    left_back:
      interface: M2
      ik_index: 2
      side: left
      position: back
      pwm_a: { timer: htim1, channel: TIM_CHANNEL_1, gpio: PE9 }
      pwm_b: { timer: htim1, channel: TIM_CHANNEL_2, gpio: PE11 }
      encoder: left_back_encoder
      speed_pid: chassis_left_back_speed
      reverse: true

    right_back:
      interface: M4
      ik_index: 3
      side: right
      position: back
      pwm_a: { timer: htim8, channel: TIM_CHANNEL_3, gpio: PC8 }
      pwm_b: { timer: htim8, channel: TIM_CHANNEL_4, gpio: PC9 }
      encoder: right_back_encoder
      speed_pid: chassis_right_back_speed
      reverse: false

  encoders:
    left_front_encoder:
      interface: M1
      timer: htim3
      channel_a: { gpio: PB4, channel: TIM_CHANNEL_1 }
      channel_b: { gpio: PB5, channel: TIM_CHANNEL_2 }

    left_back_encoder:
      interface: M2
      timer: htim2
      channel_a: { gpio: PA15, channel: TIM_CHANNEL_1 }
      channel_b: { gpio: PB3, channel: TIM_CHANNEL_2 }

    right_front_encoder:
      interface: M3
      timer: htim5
      channel_a: { gpio: PA0, channel: TIM_CHANNEL_1 }
      channel_b: { gpio: PA1, channel: TIM_CHANNEL_2 }

    right_back_encoder:
      interface: M4
      timer: htim4
      channel_a: { gpio: PD12, channel: TIM_CHANNEL_1 }
      channel_b: { gpio: PD13, channel: TIM_CHANNEL_2 }
```

## 字段说明

### robot

| 字段 | 必填 | 可选值/示例 | 说明 |
|---|---:|---|---|
| `name` | 是 | `LittleCar2026` | 机器人名字，用于生成配置名或调试打印 |
| `target` | 是 | `default_car` | 目标硬件/固件目标名 |
| `chassis_type` | 是 | `differential_drive` | 底盘类型；当前库主要支持差速底盘 |

### geometry.chassis

| 字段 | 必填 | 示例 | 说明 |
|---|---:|---|---|
| `wheel_radius_m` | 是 | `0.022` | 轮子半径，单位 m |
| `track_width_m` | 建议 | `0.13` | 左右轮中心距，单位 m，便于人工检查 |
| `half_track_m` | 是 | `0.065` | 半轮距，单位 m；差速 IK 公式直接使用 |

`half_track_m = track_width_m / 2`。如果两者都写，生成脚本可以检查它们是否一致。

### communication.uart

每个 UART 节点名可以自定义，例如 `debug`、`remote`、`vision`。

| 字段 | 必填 | 可选值/示例 | 说明 |
|---|---:|---|---|
| `logical_id` | 可选 | `Debug` | 软件逻辑名 |
| `handle` | 是 | `huart1` | HAL 串口句柄 |
| `baudrate` | 是 | `115200` | 波特率 |
| `tx_mode` | 可选 | `polling`/`interrupt`/`dma` | 发送方式 |
| `rx_mode` | 可选 | `polling`/`interrupt`/`dma`/`idle_dma` | 接收方式 |
| `rx_buffer_size` | 接收时建议 | `64`/`128` | 接收缓冲区大小 |
| `rx_callback` | 接收时可选 | `Debug_OnUartRx` | 收到数据后调用的处理函数名 |

如果串口只用于打印，最小配置可以只写：

```yaml
communication:
  uart:
    debug:
      handle: huart1
      baudrate: 115200
      tx_mode: polling
```

### messages

`messages` 描述消息总线中的发布订阅关系。消息名建议使用数据类型名，订阅函数建议使用 `模块名_消息名`。

| 字段 | 必填 | 示例 | 说明 |
|---|---:|---|---|
| `publisher` | 是 | `RemoteDriver` | 谁发布这个数据 |
| `subscribers` | 是 | `Chassis_RemoteData` | 谁接收这个数据，可以有多个 |

当前底盘闭环最核心的两个消息：

```yaml
RemoteData:
  publisher: RemoteDriver
  subscribers:
    - Chassis_RemoteData

MotorFeedback:
  publisher: MotorDriver
  subscribers:
    - Chassis_MotorFeedback
```

建议数据含义：

- `RemoteData`：遥控器/上层给底盘的期望值，例如 `vx`、`vw`、`enable`
- `MotorFeedback`：电机编码器反馈值，例如四个轮子的实际速度和编码器计数

### control.chassis_ik

| 字段 | 必填 | 可选值/示例 | 说明 |
|---|---:|---|---|
| `type` | 是 | `differential_drive` | 逆运动学类型 |
| `config.wheel_radius_m` | 是 | `0.022` | 轮子半径，单位 m |
| `config.half_track_m` | 是 | `0.065` | 半轮距，单位 m |

差速 IK 使用公式：

```text
left_wheel  = (vx - vw * half_track_m) / wheel_radius_m
right_wheel = (vx + vw * half_track_m) / wheel_radius_m
```

输出顺序固定为：

```text
0 = left_front
1 = right_front
2 = left_back
3 = right_back
```

### control.pid

每个 PID 节点名可以自定义，但必须和电机的 `speed_pid` 字段对应。

| 字段 | 必填 | 示例 | 说明 |
|---|---:|---|---|
| `kp` | 是 | `1.2` | 比例系数 |
| `ki` | 是 | `0.05` | 积分系数 |
| `kd` | 是 | `0.01` | 微分系数 |
| `output_limit` | 建议 | `1000` | PID 输出限幅；当前电机控制量建议为 `±1000` |
| `integral_limit` | 建议 | `1000` | 积分项限幅 |
| `integral_separation_threshold` | 可选 | `100.0` | 积分分离阈值；误差小于该值才积分 |
| `R` | `kd` 不为 0 时建议 | `50.0` | TD 微分跟踪器速度因子 |
| `T` | 是 | `0.001`/`0.01` | PID 控制周期，单位 s；不写或为 0 时 PID 不更新 |

`T` 必须和实际调用 `PID::Update()` 的周期一致。比如 1ms 调一次写 `0.001`，10ms 调一次写 `0.01`。

Yahboom 电机教程里的外部速度控制量是 `±1000`，PWM 脉宽内部再映射到 `±1999`，所以速度环 PID 如果直接输出电机控制量，`output_limit` 建议先写 `1000`。

### hardware.motors

每个电机节点名建议使用固定四轮命名：

```text
left_front
right_front
left_back
right_back
```

| 字段 | 必填 | 可选值/示例 | 说明 |
|---|---:|---|---|
| `interface` | 建议 | `M1`/`M2`/`M3`/`M4` | 板子丝印接口名 |
| `ik_index` | 是 | `0`/`1`/`2`/`3` | 对应 IK 输出数组下标 |
| `side` | 是 | `left`/`right` | 左右侧 |
| `position` | 是 | `front`/`back` | 前后位置 |
| `pwm_a.timer` | 是 | `htim1` | A 相 PWM 定时器 |
| `pwm_a.channel` | 是 | `TIM_CHANNEL_3` | A 相 PWM 通道 |
| `pwm_a.gpio` | 建议 | `PE13` | A 相 GPIO，方便查线 |
| `pwm_a.complementary` | 可选 | `true`/`false` | 是否为 `CHxN` 互补输出 |
| `pwm_b.timer` | 是 | `htim1` | B 相 PWM 定时器 |
| `pwm_b.channel` | 是 | `TIM_CHANNEL_4` | B 相 PWM 通道 |
| `pwm_b.gpio` | 建议 | `PE14` | B 相 GPIO，方便查线 |
| `pwm_b.complementary` | 可选 | `true`/`false` | 是否为 `CHxN` 互补输出 |
| `encoder` | 是 | `left_front_encoder` | 绑定的编码器节点名 |
| `speed_pid` | 是 | `chassis_left_front_speed` | 绑定的速度环 PID |
| `reverse` | 是 | `true`/`false` | 电机方向是否取反 |

`complementary: true` 表示 STM32 高级定时器的 `CHxN` 输出，启动时应使用 `HAL_TIMEx_PWMN_Start()`，普通通道使用 `HAL_TIM_PWM_Start()`。

当前约定的 IK 顺序：

```text
left_front  -> ik_index: 0
right_front -> ik_index: 1
left_back   -> ik_index: 2
right_back  -> ik_index: 3
```

Yahboom 板子的硬件接口顺序是：

```text
M1 = left_front
M2 = left_back
M3 = right_front
M4 = right_back
```

注意：不要把 `M1/M2/M3/M4` 当成 IK 数组顺序，代码生成时应优先使用 `ik_index`。

### hardware.encoders

每个编码器节点名必须能被电机的 `encoder` 字段引用。

| 字段 | 必填 | 示例 | 说明 |
|---|---:|---|---|
| `interface` | 建议 | `M1` | 对应电机接口 |
| `timer` | 是 | `htim3` | 编码器模式定时器 |
| `channel_a.gpio` | 建议 | `PB4` | A 相 GPIO |
| `channel_a.channel` | 是 | `TIM_CHANNEL_1` | A 相定时器通道 |
| `channel_b.gpio` | 建议 | `PB5` | B 相 GPIO |
| `channel_b.channel` | 是 | `TIM_CHANNEL_2` | B 相定时器通道 |

编码器定时器应配置为 Encoder Mode，通常使用 CH1 和 CH2。

## 最小配置

如果只是先让差速底盘跑起来，可以先保留这些部分：

```yaml
robot:
  name: LittleCar2026
  target: default_car
  chassis_type: differential_drive

control:
  chassis_ik:
    type: differential_drive
    config:
      wheel_radius_m: 0.022
      half_track_m: 0.065

  pid:
    chassis_left_front_speed:  { kp: 1.2, ki: 0.05, kd: 0.0, output_limit: 1000, integral_limit: 1000, T: 0.001 }
    chassis_right_front_speed: { kp: 1.2, ki: 0.05, kd: 0.0, output_limit: 1000, integral_limit: 1000, T: 0.001 }
    chassis_left_back_speed:   { kp: 1.2, ki: 0.05, kd: 0.0, output_limit: 1000, integral_limit: 1000, T: 0.001 }
    chassis_right_back_speed:  { kp: 1.2, ki: 0.05, kd: 0.0, output_limit: 1000, integral_limit: 1000, T: 0.001 }

hardware:
  motors:
    left_front:  { ik_index: 0, side: left,  position: front, encoder: left_front_encoder,  speed_pid: chassis_left_front_speed,  reverse: true }
    right_front: { ik_index: 1, side: right, position: front, encoder: right_front_encoder, speed_pid: chassis_right_front_speed, reverse: false }
    left_back:   { ik_index: 2, side: left,  position: back,  encoder: left_back_encoder,   speed_pid: chassis_left_back_speed,   reverse: true }
    right_back:  { ik_index: 3, side: right, position: back,  encoder: right_back_encoder,  speed_pid: chassis_right_back_speed,  reverse: false }
```

这个最小配置省略了具体 PWM 和编码器引脚，只适合早期算法/生成器调试。真正上车时应使用完整模板。
