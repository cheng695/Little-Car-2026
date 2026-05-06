#ifndef PID_HPP
#define PID_HPP

#include <algorithm>

namespace ALG::PID
{
    /**
     * @brief PID控制器参数。
     */
    struct PidConfig
    {
        /** 比例系数。 */
        float kp = 0.0f;
        /** 积分系数。 */
        float ki = 0.0f;
        /** 微分系数。 */
        float kd = 0.0f;

        /** 输出限幅，设置为正数时生效。 */
        float output_limit = 0.0f;
        /** 积分限幅，设置为正数时生效。 */
        float integral_limit = 0.0f;
        /** 积分分离阈值，设置为正数时生效。 */
        float integral_separation_threshold = 0.0f;

        /** TD微分跟踪器速度因子。 */
        float R = 0.0f;
        /** 控制周期，单位秒。 */
        float T = 0.0f;
    };

    /**
     * @brief 带TD微分先行的PID控制器。
     */
    class PID
    {
    public:
        /**
         * @brief 构造PID控制器。
         *
         * @param config PID控制器参数。
         */
        explicit PID(const PidConfig &config);

        /**
         * @brief 设置PID控制器参数。
         *
         * @param config 新的PID控制器参数。
         */
        void SetConfig(const PidConfig &config);

        /**
         * @brief 重置PID内部状态。
         */
        void Reset();

        /**
         * @brief 更新PID输出。
         *
         * @param target 目标值。
         * @param feedback 反馈值。
         * @return float PID输出值。
         */
        float Update(float target, float feedback);

        /**
         * @brief 获取最近一次PID输出。
         *
         * @return float PID输出值。
         */
        float GetOutput() const;

    private:
        /**
         * @brief 初始化TD微分跟踪器状态。
         *
         * @param input 当前反馈值。
         */
        void InitTd(float input);

        /**
         * @brief 更新TD微分跟踪器。
         *
         * @param input 输入信号。
         */
        void UpdateTd(float input);

        /**
         * @brief 获取TD微分估计量。
         *
         * @return float 微分估计量。
         */
        float GetTdDerivative() const;

        /**
         * @brief 判断本次误差是否允许积分。
         *
         * @param error 当前误差。
         * @return true 允许积分。
         * @return false 不允许积分。
         */
        bool CanIntegrate(float error) const;

        /**
         * @brief 对积分项进行限幅。
         */
        void ClampIntegral();

        /**
         * @brief 对输出项进行限幅。
         */
        void ClampOutput();

        /**
         * @brief 输出饱和时回退本次积分累积。
         *
         * @param error 当前误差。
         */
        bool AntiWindup(float error);

        /**
         * @brief 根据当前PID状态计算未限幅输出。
         *
         * @param error 当前误差。
         * @return float 未限幅输出值。
         */
        float CalculateOutput(float error) const;

        PidConfig config_;

        /** TD跟踪状态量。 */
        float td_value_ = 0.0f;
        /** TD微分估计量。 */
        float td_derivative_ = 0.0f;
        /** 误差积分值。 */
        float integral_ = 0.0f;
        /** 最近一次PID输出。 */
        float output_ = 0.0f;
        /** TD是否已经根据当前反馈值完成初始化。 */
        bool td_initialized_ = false;
    };
}

#endif // !PID_HPP
