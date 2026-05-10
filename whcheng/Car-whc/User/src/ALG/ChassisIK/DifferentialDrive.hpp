#ifndef DIFFERENTIALDRIVE_HPP
#define DIFFERENTIALDRIVE_HPP

#include "CalculationBase.hpp"

namespace ALG::ChassisIK
{
    // 差速底盘逆运动学。
    // 将底盘的前进速度 vx 和旋转速度 vw 解算成左右两侧轮子的目标角速度。
    class Diff_IK : public InverseKinematicsBase
    {
    public:
        explicit Diff_IK(const ChassisIKConfig &config)
            : InverseKinematicsBase(config)
        {}

        // 设置底盘目标速度并立即完成一次逆解。
        // vx: 前进线速度，单位 m/s。
        // vw: 旋转角速度，单位 rad/s。
        void DiffInvKinematics(float vx, float vw)
        {
            SetSignal_xw(vx, vw);
            InvKinematics();
        }

        // 差速底盘公式:
        // left_wheel = (vx - vw * half_track) / wheel_radius
        // right_wheel = (vx + vw * half_track) / wheel_radius
        // 输出单位为 rad/s。
        void InvKinematics()
        {
            if (config_.wheel_radius == 0.0f)
            {
                Set_w0w1w2w3(0.0f, 0.0f, 0.0f, 0.0f);
                return;
            }

            const float left_wheel = (Signal_x + Signal_w * config_.half_track) / config_.wheel_radius;
            const float right_wheel = (-Signal_x + Signal_w * config_.half_track) / config_.wheel_radius;

            Set_w0w1w2w3(left_wheel, right_wheel, left_wheel, right_wheel);
        }
    };
}

#endif // !DIFFERENTIALDRIVE_HPP
