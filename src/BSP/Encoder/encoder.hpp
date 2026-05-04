#ifndef ENCODER_HPP
#define ENCODER_HPP

#include <cmath>
#include "drv_pwm.hpp"

namespace BSP::ENCODER
{
    /**
     * @brief 编码器基础计数接口。
     */
    class IEncoder
    {
    public:
        virtual ~IEncoder() = default;

        /**
         * @brief 启动编码器计数。
         *
         * @return true 启动成功。
         * @return false 启动失败。
         */
        virtual bool Start() = 0;

        /**
         * @brief 停止编码器计数。
         *
         * @return true 停止成功。
         * @return false 停止失败。
         */
        virtual bool Stop() = 0;

        /**
         * @brief 获取软件累计计数。
         *
         * @return int32_t 累计计数值。
         */
        virtual int32_t GetCount() const = 0;

        /**
         * @brief 获取两次读取之间的计数增量。
         *
         * @return int32_t 带符号计数增量。
         */
        virtual int32_t GetDelta() = 0;

        /**
         * @brief 清零编码器计数。
         */
        virtual void Reset() = 0;
    };

    /**
     * @brief 基于STM32 HAL定时器编码器模式的编码器实现。
     */
    class HALEncoder : public IEncoder
    {
    public:
        /**
         * @brief 构造HAL编码器对象。
         *
         * @param htim 定时器句柄。
         */
        explicit HALEncoder(TIM_HandleTypeDef *htim)
            : htim_(htim)
        {
        }

        /**
         * @brief 启动定时器编码器模式。
         *
         * @return true 启动成功。
         * @return false 定时器无效或HAL启动失败。
         */
        bool Start() override
        {
            if (htim_ == nullptr)
            {
                return false;
            }

            last_count_ = GetRawCount();
            return HAL_TIM_Encoder_Start(htim_, TIM_CHANNEL_ALL) == HAL_OK;
        }

        /**
         * @brief 停止定时器编码器模式。
         *
         * @return true 停止成功。
         * @return false 定时器无效或HAL停止失败。
         */
        bool Stop() override
        {
            if (htim_ == nullptr)
            {
                return false;
            }

            return HAL_TIM_Encoder_Stop(htim_, TIM_CHANNEL_ALL) == HAL_OK;
        }

        /**
         * @brief 获取软件累计计数。
         *
         * @return int32_t 累计计数值。
         */
        int32_t GetCount() const override
        {
            return total_count_;
        }

        /**
         * @brief 获取本次和上次读取之间的计数增量。
         *
         * @return int32_t 带符号计数增量。
         */
        int32_t GetDelta() override
        {
            const uint16_t now = GetRawCount();
            const int32_t delta = static_cast<int16_t>(now - last_count_);

            last_count_ = now;
            total_count_ += delta;

            return delta;
        }

        /**
         * @brief 清零硬件计数器和软件累计计数。
         */
        void Reset() override
        {
            if (htim_ == nullptr)
            {
                return;
            }

            __HAL_TIM_SET_COUNTER(htim_, 0);
            last_count_ = 0;
            total_count_ = 0;
        }

    private:
        /**
         * @brief 读取硬件定时器原始计数值。
         *
         * @return uint16_t 原始16位计数值。
         */
        uint16_t GetRawCount() const
        {
            return static_cast<uint16_t>(__HAL_TIM_GET_COUNTER(htim_));
        }

        TIM_HandleTypeDef *htim_;
        uint16_t  last_count_ = 0;
        int32_t total_count_ = 0;
    };

    /**
     * @brief 编码器测量数据计算器。
     */
    class EncoderData
    {
    public:
        /**
         * @brief 构造编码器测量数据对象。
         *
         * @param encoder 编码器基础计数接口。
         * @param CPR 每转计数值。
         * @param dt 更新周期，单位为秒。
         */
        EncoderData(IEncoder &encoder, uint32_t CPR, float dt)
            : encoder_(encoder),
              cpr_(CPR), dt_(dt)
        {
        }

        /**
         * @brief 启动编码器。
         *
         * @return true 启动成功。
         * @return false 启动失败。
         */
        bool Start()
        {
            return encoder_.Start();
        }

        /**
         * @brief 停止编码器。
         *
         * @return true 停止成功。
         * @return false 停止失败。
         */
        bool Stop()
        {
            return encoder_.Stop();
        }

        /**
         * @brief 清零编码器和缓存的测量数据。
         */
        void Reset()
        {
            encoder_.Reset();
            zero_offset_ = 0;
            ClearData();
        }

        /**
         * @brief 将当前位置设置为角度零点。
         */
        void SetZero()
        {
            zero_offset_ = encoder_.GetCount();
        }

        /**
         * @brief 更新编码器速度和角度测量数据。
         */
        void Update()
        {
            if (!IsConfigValid())
            {
                ClearData();
                return;
            }

            delta_ = encoder_.GetDelta();
            const float revolutions = static_cast<float>(delta_) / static_cast<float>(cpr_);
            rpm_ = revolutions / dt_ * 60.0f;
            rads_ = revolutions / dt_ * 6.2831853f;

            const int32_t count = encoder_.GetCount() - zero_offset_;
            total_angle_deg_ = static_cast<float>(count) / static_cast<float>(cpr_) * 360.0f;
            total_angle_rad_ = total_angle_deg_ * 0.0174532925f;

            float angle = std::fmod(GetTotalAngleDeg(), 360.0f);
            if (angle < 0.0f) { angle += 360.0f; }
            angle_deg_ = angle;
            angle_rad_ = angle_deg_ * 0.0174532925f;
        }

        /**
         * @brief 获取软件累计计数。
         *
         * @return int32_t 累计计数值。
         */
        int32_t GetCount() const
        {
            return encoder_.GetCount();
        }

        /**
         * @brief 获取最近一次更新得到的计数增量。
         *
         * @return int32_t 最近一次更新的计数增量。
         */
        int32_t GetDelta() const
        {
            return delta_;
        }

        /**
         * @brief 获取转速。
         *
         * @return float 转速，单位RPM。
         */
        float GetRpm() const
        {
            return rpm_;
        }

        /**
         * @brief 获取角速度。
         *
         * @return float 角速度，单位rad/s。
         */
        float GetRads() const
        {
            return rads_;
        }

        /**
         * @brief 获取累计角度。
         *
         * @return float 累计角度，单位度，可超过0~360范围。
         */
        float GetTotalAngleDeg() const
        {
            return total_angle_deg_;
        }

        /**
         * @brief 获取累计弧度。
         *
         * @return float 累计弧度，单位rad。
         */
        float GetTotalAngleRad() const
        {
            return total_angle_rad_;
        }

        /**
         * @brief 获取机械角度。
         *
         * @return float 机械角度，单位度，范围为0~360。
         */
        float GetAngleDeg() const
        {
            return angle_deg_;
        }

        /**
         * @brief 获取机械弧度。
         *
         * @return float 机械弧度，单位rad。
         */
        float GetAngleRad() const
        {
            return angle_rad_;
        }

    private:
        /**
         * @brief 判断编码器换算配置是否有效。
         *
         * @return true 配置有效。
         * @return false 配置无效。
         */
        bool IsConfigValid() const
        {
            return dt_ > 0.0f && cpr_ != 0;
        }

        /**
         * @brief 清空缓存的测量数据。
         */
        void ClearData()
        {
            delta_ = 0;
            rpm_ = 0.0f;
            rads_ = 0.0f;
            total_angle_deg_ = 0.0f;
            total_angle_rad_ = 0.0f;
            angle_deg_ = 0.0f;
            angle_rad_ = 0.0f;
        }

        IEncoder &encoder_;
        uint32_t cpr_;
        float dt_;

        int32_t zero_offset_ = 0;
        int32_t delta_ = 0;

        float rpm_ = 0.0f;
        float rads_ = 0.0f;
        float total_angle_deg_ = 0.0f;
        float total_angle_rad_ = 0.0f;
        float angle_deg_ = 0.0f;
        float angle_rad_ = 0.0f;
    };
}

#endif // !ENCODER_HPP
