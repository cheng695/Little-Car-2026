#ifndef MOTOR_310_HPP
#define MOTOR_310_HPP

#include <stdint.h>
#include <cmath>
#include <algorithm>

#include "MotorBase.hpp"
#include "encoder.hpp"


namespace BSP::Motor::_310
{
    /**
     * @brief 电机逻辑ID。
     */
    enum class MotorId : uint8_t
    {
        LeftForward = 0,
        RightForward,
        LeftBackward,
        RightBackward,
        Count
    };

    /**
     * @brief 电机换算参数。
     */
    struct Parameters
    {
        /** 减速比，例如20表示编码器轴20圈对应输出轴1圈。 */
        float reduction_ratio = 1.0f;
        /** 编码器侧数据换算到输出轴侧数据的系数。 */
        float encoder_to_output = 1.0f;

        /**
         * @brief 构造电机换算参数。
         *
         * @param rr 减速比。
         */
        explicit constexpr Parameters(float rr)
            : reduction_ratio(rr),
              encoder_to_output(rr > 0.0f ? 1.0f / rr : 0.0f)
        {
        }
    };

    /**
     * @brief 电机硬件绑定配置。
     */
    struct MotorConfig
    {
        /** 电机逻辑ID。 */
        MotorId id;

        /** PWM输出通道。 */
        DRV::PWM::IPwm *pwm_a;
        /** 方向控制引脚1。 */
        DRV::PWM::IPwm *pwm_b;
        /** 方向控制引脚2。 */
        /** 电机编码器测量对象。 */
        BSP::ENCODER::EncoderData *encoder;

        /** 电机换算参数。 */
        Parameters params;
    };

    /**
     * @brief 310电机组封装，使用PWM、GPIO方向引脚和编码器反馈。
     *
     * @tparam N 电机数量。
     */
    template <uint8_t N>
    class Motor310Base : public BSP::Motor::MotorBase<N>
    {
    public:
        /**
         * @brief 通过电机配置表构造电机组。
         *
         * @param configs 电机配置表。
         */
        explicit Motor310Base(const MotorConfig (&configs)[N])
            : configs_(configs)
        {
        }

        /**
         * @brief 启动所有电机的PWM和编码器。
         *
         * @return true 所有有效电机启动成功。
         * @return false 至少一个电机启动失败。
         */
        bool Start() override
        {
            bool ok = true;

            for (uint8_t i = 0; i < N; ++i)
            {
                ok = StartMotor(i) && ok;
            }

            return ok;
        }

        /**
         * @brief 停止所有电机。
         *
         * @return true 所有有效电机停止成功。
         * @return false 至少一个电机停止失败。
         */
        bool Stop() override
        {
            bool ok = true;

            for (uint8_t i = 0; i < N; ++i)
            {
                ok = StopMotor(i) && ok;
            }

            return ok;
        }

        /**
         * @brief 从编码器更新所有电机反馈数据。
         */
        void Update() override
        {
            for (uint8_t i = 0; i < N; ++i)
            {
                UpdateMotor(i);
            }
        }

        /**
         * @brief 按电机序号设置占空比。
         *
         * @param id 电机序号，范围1~N。
         * @param duty 占空比指令，范围-1000~1000，符号表示方向。
         * @return true 指令已接受。
         * @return false 电机序号无效或电机资源无效。
         */
        bool SetDuty(uint8_t id, int16_t duty) override
        {
            if (!this->IsValidId(id))
            {
                return false;
            }

            return SetDutyByIndex(this->ToIndex(id), duty);
        }

        /**
         * @brief 按电机逻辑ID设置占空比。
         *
         * @param id 电机逻辑ID。
         * @param duty 占空比指令，范围-1000~1000，符号表示方向。
         * @return true 指令已接受。
         * @return false 未找到电机ID或电机资源无效。
         */
        bool SetDuty(MotorId id, int16_t duty)
        {
            const int8_t index = FindIndex(id);
            if (index < 0)
            {
                return false;
            }

            return SetDutyByIndex(static_cast<uint8_t>(index), duty);
        }

    private:
        /**
         * @brief 启动指定下标的电机。
         *
         * @param index 电机数组下标。
         * @return true 启动成功。
         * @return false 启动失败。
         */
        bool StartMotor(uint8_t index)
        {
            const MotorConfig &config = configs_[index];
            auto &data = this->unit_data_[index];

            if (config.pwm_a == nullptr || config.pwm_b == nullptr)
            {
                data.enabled = false;
                data.status = MotorStatus::EncoderFault;
                return false;
            }

            const bool encoder_ok = config.encoder == nullptr ? true : config.encoder->Start();
            const bool pwm_ok = config.pwm_a->Start() && config.pwm_b->Start();

            data.enabled = encoder_ok && pwm_ok;
            data.status = data.enabled ? MotorStatus::Stopped : MotorStatus::EncoderFault;

            return data.enabled;
        }

        /**
         * @brief 停止指定下标的电机。
         *
         * @param index 电机数组下标。
         * @return true 停止成功。
         * @return false 停止失败。
         */
        bool StopMotor(uint8_t index)
        {
            const MotorConfig &config = configs_[index];
            auto &data = this->unit_data_[index];

            bool ok = true;
            SetDutyByIndex(index, 0);

            if (config.pwm_a != nullptr)
            {
                ok = config.pwm_a->Stop() && ok;
            }

            if (config.pwm_b != nullptr)
            {
                ok = config.pwm_b->Stop() && ok;
            }

            if (config.encoder != nullptr)
            {
                ok = config.encoder->Stop() && ok;
            }

            data.enabled = false;
            data.status = MotorStatus::Stopped;

            return ok;
        }

        /**
         * @brief 更新指定下标电机的编码器反馈和状态。
         *
         * @param index 电机数组下标。
         */
        void UpdateMotor(uint8_t index)
        {
            const MotorConfig &config = configs_[index];

            if (config.encoder != nullptr)
            {
                config.encoder->Update();
                Configure(index);
            }
            UpdateStatus(index);
        }

        /**
         * @brief 按数组下标设置电机占空比。
         *
         * @param index 电机数组下标。
         * @param duty 占空比指令，范围-1000~1000，符号表示方向。
         * @return true 设置成功。
         * @return false 电机资源无效。
         */
        bool SetDutyByIndex(uint8_t index, int16_t duty)
        {
            const MotorConfig &config = configs_[index];
            auto &data = this->unit_data_[index];

            if (config.pwm_a == nullptr || config.pwm_b == nullptr)
            {
                return false;
            }

            duty = std::clamp<int16_t>(duty, -1000, 1000);

            if (duty > 0)
            {
                config.pwm_a->SetDuty(static_cast<uint16_t>(duty));
                config.pwm_b->SetDuty(0);
            }
            else if (duty < 0)
            {
                config.pwm_a->SetDuty(0);
                config.pwm_b->SetDuty(static_cast<uint16_t>(-duty));
            }
            else
            {
                config.pwm_a->SetDuty(0);
                config.pwm_b->SetDuty(0);
            }

            data.duty = duty;
            return true;
        }

        /**
         * @brief 将编码器侧数据换算为输出轴侧数据。
         *
         * @param index 电机数组下标。
         */
        void Configure(uint8_t index)
        {
            const MotorConfig &config = configs_[index];
            auto &data = this->unit_data_[index];
            const auto &encoder = *config.encoder;
            const auto &params = config.params;

            data.encoder_count = encoder.GetCount();
            data.encoder_delta = encoder.GetDelta();
            data.encoder_velocity_rpm = encoder.GetRpm();
            data.encoder_velocity_rads = encoder.GetRads();
            data.encoder_angle_deg = encoder.GetTotalAngleDeg();
            data.encoder_angle_rad = encoder.GetTotalAngleRad();

            data.velocity_rpm = data.encoder_velocity_rpm * params.encoder_to_output;
            data.velocity_rads = data.encoder_velocity_rads * params.encoder_to_output;
            data.add_angle_deg = data.encoder_angle_deg * params.encoder_to_output;
            data.add_angle_rad = data.encoder_angle_rad * params.encoder_to_output;

            data.last_angle_deg = data.angle_deg;
            data.angle_deg = Normalize360(data.add_angle_deg);
            data.angle_rad = data.angle_deg * kDegToRad;
        }

        /**
         * @brief 更新指定电机的运行状态。
         *
         * @param index 电机数组下标。
         */
        void UpdateStatus(uint8_t index)
        {
            auto &data = this->unit_data_[index];

            if (!data.enabled)
            {
                data.status = MotorStatus::Stopped;
                return;
            }

            if (data.duty == 0)
            {
                data.status = MotorStatus::Stopped;
                return;
            }

            data.status = MotorStatus::Running;
        }

        /**
         * @brief 根据逻辑ID查找电机数组下标。
         *
         * @param id 电机逻辑ID。
         * @return int8_t 找到时返回数组下标，未找到返回-1。
         */
        int8_t FindIndex(MotorId id) const
        {
            for (uint8_t i = 0; i < N; ++i)
            {
                if (configs_[i].id == id)
                {
                    return static_cast<int8_t>(i);
                }
            }

            return -1;
        }

        /**
         * @brief 将角度归一化到0~360度。
         *
         * @param angle 输入角度，单位度。
         * @return float 归一化后的角度。
         */
        static float Normalize360(float angle)
        {
            angle = std::fmod(angle, 360.0f);

            if (angle < 0.0f)
            {
                angle += 360.0f;
            }

            return angle;
        }

        static constexpr float kDegToRad = 0.0174532925f;

        const MotorConfig (&configs_)[N];
    };


    template <uint8_t N>
    class Motor310 : public Motor310Base<N>
    {
    public:
        explicit Motor310(const MotorConfig (&configs)[N])
            : Motor310Base<N>(configs)
        {
        }
    };
}

#endif // !MOTOR_310_HPP
