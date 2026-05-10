#include "CommunicationTask.hpp"

#include "cmsis_os.h"
#include "robot_messages.hpp"
#include "robot_runtime.hpp"

#include <stdint.h>
#include <string.h>

namespace
{
    uint8_t send_str2[6 * sizeof(float) + 4] = {};

    RobotMessages::ChassisTarget chassis_targt{};
    RobotMessages::MotorFeedback motor_feedback{};
    RobotMessages::ChassisIKMsg chassisIK_target{};
    
    void OnChassisTarget(const RobotMessages::ChassisTarget &msg)
    {
        chassis_targt = msg;
    }
    void OnMotorFeeedback(const RobotMessages::MotorFeedback &msg)
    {
        motor_feedback = msg;
    }
    void OnChassisIK(const RobotMessages::ChassisIKMsg &msg)
    {
        chassisIK_target = msg;
    }

    void InitMessageSubscribe()
    {
        RobotMessages::SubscribeChassisTarget(OnChassisTarget);
        RobotMessages::SubscribeMotorFeedback(OnMotorFeeedback);
        RobotMessages::SubscribeChassisIKMsg(OnChassisIK);
    }
}

void vofa_send(float x1, float x2, float x3, float x4, float x5, float x6)
{
    const float data[6] = {x1, x2, x3, x4, x5, x6};
    memcpy(send_str2, data, sizeof(data));

    send_str2[sizeof(data) + 0] = 0x00;
    send_str2[sizeof(data) + 1] = 0x00;
    send_str2[sizeof(data) + 2] = 0x80;
    send_str2[sizeof(data) + 3] = 0x7F;

    DRV::UART::UartManager::Instance().Send(
        DRV::UART::UartId::Debug,
        send_str2,
        sizeof(send_str2)
    );
}

void Debug_OnUartRx(DRV::UART::UartId id, const DRV::UART::UartData &data)
{

}

extern "C" void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *huart, uint16_t Size)
{
    RobotRuntime::OnUartRxEvent(huart, Size);
}

extern "C" void CommTask(void const *argument)
{
    RobotRuntime::InitUarts();
    InitMessageSubscribe();

    for (;;)
    {
        vofa_send(chassisIK_target.motors[0].target, 
                  motor_feedback.motors[0].angle_deg, // 右后
                  motor_feedback.motors[1].angle_deg, 
                  motor_feedback.motors[2].angle_deg, // 右前
                  motor_feedback.motors[3].angle_deg, 
                  0.0f);
        osDelay(1);
    }
}
