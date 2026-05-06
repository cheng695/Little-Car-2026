#ifndef DIFFERENTIALDRIVE_HPP
#define DIFFERENTIALDRIVE_HPP

#include "CalculationBase.hpp"

namespace ALG::ChassisIK
{
    class Diff_IK : public InverseKinematicsBase
    {
    public:
        explicit Diff_IK(const ChassisIKConfig &config)
            : InverseKinematicsBase(config)
        {}

        void DiffInvKinematics(float vx, float vw)
        {
            SetSignal_xw(vx, vw);
            InvKinematics();
        }

        void InvKinematics()
        {
            if (config_.wheel_radius == 0.0f)
            {
                Set_w0w1w2w3(0.0f, 0.0f, 0.0f, 0.0f);
                return;
            }

            const float left_wheel = (Signal_x - Signal_w * config_.half_track) / config_.wheel_radius;
            const float right_wheel = (Signal_x + Signal_w * config_.half_track) / config_.wheel_radius;

            Set_w0w1w2w3(left_wheel, right_wheel, left_wheel, right_wheel);
        }
    };
}

#endif // !DIFFERENTIALDRIVE_HPP
