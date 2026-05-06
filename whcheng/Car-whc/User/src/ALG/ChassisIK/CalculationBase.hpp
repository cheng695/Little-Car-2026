#ifndef CHASSIS_CALCULATION_BASE_HPP
#define CHASSIS_CALCULATION_BASE_HPP

namespace ALG::ChassisIK
{
    struct ChassisIKConfig
    {
        float wheel_radius = 1.0f;
        float half_track = 1.0f;
    };

    class InverseKinematicsBase
    {
    public:
        virtual ~InverseKinematicsBase() = default;

        explicit InverseKinematicsBase(const ChassisIKConfig &config)
            : config_(config)
        {
            Set_w0w1w2w3(0.0f, 0.0f, 0.0f, 0.0f);
        }

        virtual void SetSignal_xw(float vx, float vw)
        {
            Signal_x = vx;
            Signal_w = vw;
        }

        virtual void SetWheelRadius(float wheel_radius)
        {
            config_.wheel_radius = wheel_radius;
        }

        virtual void SetHalfTrack(float half_track)
        {
            config_.half_track = half_track;
        }

        virtual void SetConfig(const ChassisIKConfig &config)
        {
            config_ = config;
        }

        float GetMotor_wheel(int index) const
        {
            if (index >= 0 && index < 4)
            {
                return Motor_wheel[index];
            }

            return 0.0f;
        }

        float GetSignal_x() const { return Signal_x; }
        float GetSignal_w() const { return Signal_w; }
        float GetWheelRadius() const { return config_.wheel_radius; }
        float GetHalfTrack() const { return config_.half_track; }
        ChassisIKConfig GetConfig() const { return config_; }

    protected:
        void Set_w0w1w2w3(float w0, float w1, float w2, float w3)
        {
            Motor_wheel[0] = w0;
            Motor_wheel[1] = w1;
            Motor_wheel[2] = w2;
            Motor_wheel[3] = w3;
        }

        float Signal_x = 0.0f;
        float Signal_w = 0.0f;
        ChassisIKConfig config_;
        float Motor_wheel[4];
    };
}

#endif // !CHASSIS_CALCULATION_BASE_HPP
