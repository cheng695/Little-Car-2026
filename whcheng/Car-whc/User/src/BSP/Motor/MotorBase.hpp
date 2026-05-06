#ifndef MOTOR_BASE_HPP
#define MOTOR_BASE_HPP

#include <stdint.h>

namespace BSP::Motor
{
    /**
     * @brief 电机运行状态。
     */
    enum class MotorStatus : uint8_t
    {
        Stopped = 0,
        Running,
        EncoderFault
    };

    /**
     * @brief 固定数量电机组基类。
     *
     * @tparam N 电机数量。
     */
    template <uint8_t N>
    class MotorBase
    {
    public:
        /**
         * @brief 电机运行数据。
         */
        struct UnitData
        {
            /** 编码器侧累计角度，单位度。 */
            float encoder_angle_deg = 0.0f;
            /** 编码器侧累计角度，单位弧度。 */
            float encoder_angle_rad = 0.0f;
            /** 编码器侧角速度，单位rad/s。 */
            float encoder_velocity_rads = 0.0f;
            /** 编码器侧转速，单位RPM。 */
            float encoder_velocity_rpm = 0.0f;

            /** 输出轴机械角度，范围0~360度。 */
            float angle_deg = 0.0f;
            /** 输出轴机械角度，单位弧度。 */
            float angle_rad = 0.0f;
            /** 输出轴角速度，单位rad/s。 */
            float velocity_rads = 0.0f;
            /** 输出轴转速，单位RPM。 */
            float velocity_rpm = 0.0f;

            /** 上一次输出轴机械角度，单位度。 */
            float last_angle_deg = 0.0f;
            /** 输出轴累计角度，单位度。 */
            float add_angle_deg = 0.0f;
            /** 输出轴累计角度，单位弧度。 */
            float add_angle_rad = 0.0f;

            /** 编码器侧软件累计计数。 */
            int32_t encoder_count = 0;
            /** 编码器最近一次更新的增量计数。 */
            int32_t encoder_delta = 0;

            /** 电机占空比指令，范围-1000~1000，符号表示方向。 */
            int16_t duty = 0;
            /** 电机是否已使能。 */
            bool enabled = false;
            /** 电机当前状态。 */
            MotorStatus status = MotorStatus::Stopped;
        };

        virtual ~MotorBase() = default;

        /**
         * @brief 启动所有电机。
         *
         * @return true 所有有效电机启动成功。
         * @return false 至少一个电机启动失败。
         */
        virtual bool Start() = 0;

        /**
         * @brief 停止所有电机。
         *
         * @return true 所有有效电机停止成功。
         * @return false 至少一个电机停止失败。
         */
        virtual bool Stop() = 0;

        /**
         * @brief 更新所有电机反馈数据。
         */
        virtual void Update() = 0;

        /**
         * @brief 按电机序号设置占空比。
         *
         * @param id 电机序号，范围1~N。
         * @param duty 占空比指令，范围-1000~1000。
         * @return true 指令已接受。
         * @return false 电机序号无效或电机资源无效。
         */
        virtual bool SetDuty(uint8_t id, int16_t duty) = 0;

        /**
         * @brief 按电机序号获取电机数据。
         *
         * @param id 电机序号，范围1~N。
         * @return const UnitData& 电机数据。
         */
        const UnitData &GetData(uint8_t id) const
        {
            return unit_data_[ToIndex(id)];
        }

        /**
         * @brief 获取输出轴机械角度。
         *
         * @param id 电机序号，范围1~N。
         * @return float 机械角度，单位度，范围0~360。
         */
        float GetAngleDeg(uint8_t id) const
        {
            return unit_data_[ToIndex(id)].angle_deg;
        }

        float getAngleDeg(uint8_t id) const
        {
            return GetAngleDeg(id);
        }

        /**
         * @brief 获取输出轴机械角度。
         *
         * @param id 电机序号，范围1~N。
         * @return float 机械角度，单位弧度。
         */
        float GetAngleRad(uint8_t id) const
        {
            return unit_data_[ToIndex(id)].angle_rad;
        }

        float getAngleRad(uint8_t id) const
        {
            return GetAngleRad(id);
        }

        /**
         * @brief 获取输出轴累计角度。
         *
         * @param id 电机序号，范围1~N。
         * @return float 累计角度，单位度。
         */
        float GetAddAngleDeg(uint8_t id) const
        {
            return unit_data_[ToIndex(id)].add_angle_deg;
        }

        float getAddAngleDeg(uint8_t id) const
        {
            return GetAddAngleDeg(id);
        }

        /**
         * @brief 获取输出轴累计角度。
         *
         * @param id 电机序号，范围1~N。
         * @return float 累计角度，单位弧度。
         */
        float GetAddAngleRad(uint8_t id) const
        {
            return unit_data_[ToIndex(id)].add_angle_rad;
        }

        float getAddAngleRad(uint8_t id) const
        {
            return GetAddAngleRad(id);
        }

        /**
         * @brief 获取输出轴角速度。
         *
         * @param id 电机序号，范围1~N。
         * @return float 角速度，单位rad/s。
         */
        float GetVelocityRads(uint8_t id) const
        {
            return unit_data_[ToIndex(id)].velocity_rads;
        }

        float getVelocityRads(uint8_t id) const
        {
            return GetVelocityRads(id);
        }

        /**
         * @brief 获取输出轴转速。
         *
         * @param id 电机序号，范围1~N。
         * @return float 转速，单位RPM。
         */
        float GetVelocityRpm(uint8_t id) const
        {
            return unit_data_[ToIndex(id)].velocity_rpm;
        }

        float getVelocityRpm(uint8_t id) const
        {
            return GetVelocityRpm(id);
        }

        /**
         * @brief 获取电机状态。
         *
         * @param id 电机序号，范围1~N。
         * @return MotorStatus 当前状态。
         */
        MotorStatus GetStatus(uint8_t id) const
        {
            return unit_data_[ToIndex(id)].status;
        }

    protected:
        static constexpr uint8_t MotorCount()
        {
            return N;
        }

        static bool IsValidId(uint8_t id)
        {
            return id > 0 && id <= N;
        }

        static uint8_t ToIndex(uint8_t id)
        {
            return IsValidId(id) ? static_cast<uint8_t>(id - 1) : 0;
        }

        UnitData unit_data_[N] = {};
    };
}

#endif // !MOTOR_BASE_HPP
