# configs

该目录用于存放机器人配置源文件。

YAML 文件用于描述整车的连接关系和硬件映射，例如：

- UART/CAN 逻辑通道与 HAL 句柄的对应关系
- 消息发布者和订阅者
- PID 参数
- 电机 PWM 定时器和通道
- 编码器定时器
- 传感器总线和地址

STM32 固件运行时不直接解析 YAML。推荐后续使用脚本读取 YAML，并生成 C++ 配置代码，例如：

- `robot_graph.cpp`
- `robot_config.hpp`
- `drv_uart_map.cpp`
- `bsp_motor_config.cpp`
- `pid_config.cpp`

如果有多台小车，可以按目标拆分配置：

```text
configs/
├── car_a.yaml
├── car_b.yaml
└── car_c.yaml
```
