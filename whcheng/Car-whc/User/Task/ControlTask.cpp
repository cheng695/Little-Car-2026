#include "ControlTask.hpp"

using namespace RobotRuntime;
using namespace RobotMessages;

namespace
{
    RobotMessages::RemoteData chassis_target{};

    void OnRemoteData(const RobotMessages::RemoteData &msg)
    {
        chassis_target = msg;
    }

    void InitMessageSubscribe()
    {
        RobotMessages::SubscribeRemoteData(OnRemoteData);
    }
}

void ReadFeedback()
{
    ChassisMotors().Update();

    RobotMessages::MotorFeedback msg{};
    msg.left_front_speed_rads = ChassisMotors().GetVelocityRads(1);
    msg.left_front_angle_rad = ChassisMotors().GetAddAngleRad(1);
    msg.right_front_speed_rads = ChassisMotors().GetVelocityRads(2);
    msg.right_front_angle_rad = ChassisMotors().GetAddAngleRad(2);
    msg.left_back_speed_rads = ChassisMotors().GetVelocityRads(3);
    msg.left_back_angle_rad = ChassisMotors().GetAddAngleRad(3);
    msg.right_back_speed_rads = ChassisMotors().GetVelocityRads(4);
    msg.right_back_angle_rad = ChassisMotors().GetAddAngleRad(4);

    PublishMotorFeedback(msg);
}

void SetTarget()
{
    RemoteData msg{};
    msg.target_forward = 1.0f;
    msg.target_rotation = 0.0f;

    PublishRemoteData(msg);
}

void Control()
{
    (void)chassis_target;
}

extern "C" void ControTask(void const *argument)
{
    InitMessageSubscribe();
    ChassisMotors().Start();

    for (;;)
    {
        ReadFeedback();
        Control();
        osDelay(1);
    }
}
