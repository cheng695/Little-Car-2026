#include "HardwareTask.hpp"

#include <algorithm>
#include <stdint.h>

#include "robot_messages.hpp"
#include "robot_runtime.hpp"
#include "cmsis_os.h"

using namespace RobotMessages;
using namespace RobotRuntime;

namespace
{
    RobotMessages::ChassisOutput motor_output{};

    void OnMotorOutput(const RobotMessages::ChassisOutput &msg)
    {
        motor_output = msg;
    }

    void InitMessageSubscribe()
    {
        RobotMessages::SubscribeChassisOutput(OnMotorOutput);
    }
}

void motor_control_logic()
{
    auto &motors = ChassisMotors();

    for (uint8_t i = 0; i < RobotConfig::kMotorCount; i++)
    {
        const uint8_t motor_id = i + 1u;
        const int16_t duty = std::clamp(motor_output.motors[i].out, -1000.0f, 1000.0f);
        motors.SetDuty(motor_id, duty);
    }  
}
extern "C" void HardwareTask(void const *argument)
{
    InitMessageSubscribe();

    for (;;) 
    {
        motor_control_logic();
        osDelay(1);
    }
}
