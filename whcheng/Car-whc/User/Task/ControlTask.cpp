#include "ControlTask.hpp"
#include "robot_messages.hpp"
#include "robot_runtime.hpp"

#include <cmath>

using namespace RobotRuntime;
using namespace RobotMessages;

namespace
{
    RobotMessages::ChassisTarget chassis_target{};
    RobotMessages::MotorFeedback motor_data{};
    RobotMessages::ChassisOutput chassis_output{};
    RobotMessages::ChassisIKMsg chassis_ik{};

    // float SinTarget(float expect)
    // {
    //     static float phase = 0.0f;
    //     constexpr float kStep = 0.005f;
    //     constexpr float kTwoPi = 6.2831853f;

    //     phase += kStep;
    //     if (phase >= kTwoPi)
    //     {
    //         phase -= kTwoPi;
    //     }

    //     return expect * std::sin(phase);
    // }
}

void ReadFeedback()
{
    auto &motors = ChassisMotors();
    motors.Update();

    for (uint8_t i = 0; i < RobotConfig::kMotorCount; i++)
    {
        const uint8_t motor_id = i + 1u;
        motor_data.motors[i].speed_rads = motors.GetVelocityRads(motor_id);
        motor_data.motors[i].speed_rpm = motors.GetVelocityRpm(motor_id);
        motor_data.motors[i].angle_rad = motors.GetAddAngleRad(motor_id);
        motor_data.motors[i].angle_deg = motors.GetAddAngleDeg(motor_id);
    }

    PublishMotorFeedback(motor_data);
}

void SetTarget()
{
    chassis_target.target_forward = 0.0f;
    chassis_target.target_rotation = 0.0f;

    PublishChassisTarget(chassis_target);
}

void Control()
{
    ChassisIK().DiffInvKinematics(chassis_target.target_forward, chassis_target.target_rotation);
    for (uint8_t i = 0; i < RobotConfig::kMotorCount; i++)
    {
        chassis_ik.motors[i].target = ChassisIK().GetMotor_wheel(i);
        ChassisSpeedPids()[i].Update(ChassisIK().GetMotor_wheel(i), motor_data.motors[i].speed_rads);
        chassis_output.motors[i].out = ChassisSpeedPids()[i].GetOutput();
    }
    
    PublishChassisOutput(chassis_output);
    PublishChassisIKMsg(chassis_ik);
}

extern "C" void ControTask(void const *argument)
{
    ChassisMotors().Start();

    for (;;)
    {
        ReadFeedback();
        SetTarget();
        Control();
        osDelay(1);
    }
}
