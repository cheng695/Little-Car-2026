#ifndef CHASSIS_CALCULATION_BASE_HPP
#define CHASSIS_CALCULATION_BASE_HPP

namespace ALG::ChassisIK
{
    // 底盘逆运动学参数。
    // wheel_radius: 轮子半径，单位 m。
    // half_track: 左右轮中心距的一半，单位 m。
    struct ChassisIKConfig
    {
        float wheel_radius = 1.0f;
        float half_track = 1.0f;
    };

    // 底盘逆运动学基类。
    // 输入为底盘目标速度，输出为 4 个轮子的目标角速度。
    class InverseKinematicsBase
    {
    public:
        virtual ~InverseKinematicsBase() = default;

        explicit InverseKinematicsBase(const ChassisIKConfig &config)
            : config_(config)
        {
            Set_w0w1w2w3(0.0f, 0.0f, 0.0f, 0.0f);
        }

        // 设置底盘目标速度。
        // vx: 车体前进线速度，单位 m/s。
        // vw: 车体旋转角速度，单位 rad/s。
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

        // 根据轮子编号读取逆解后的目标轮速，单位 rad/s。
        // 当前约定: 0 左前，1 右前，2 左后，3 右后。
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
        // 保存 4 个轮子的目标角速度，单位 rad/s。
        // 参数顺序: 左前、左后、右前、右后。
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
