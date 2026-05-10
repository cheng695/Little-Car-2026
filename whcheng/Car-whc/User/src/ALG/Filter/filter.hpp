#ifndef FILTER_HPP
#define FILTER_HPP

namespace ALG::Filter
{
    /**
     * @brief 一阶低通滤波器配置。
     */
    struct LowPassFilterConfig
    {
        float alpha;
        float initial_output;
    };

    /**
     * @brief TD微分跟踪器配置。
     */
    struct TDFilterConfig
    {
        float r;
        float h;
        float initial_v1;
        float initial_v2;
    };

    /**
     * @brief 一阶低通滤波器。
     */
    class LowPassFilter
    {
    public:
        /**
         * @brief 构造一阶低通滤波器对象。
         */
        LowPassFilter() = default;

        /**
         * @brief 使用配置构造一阶低通滤波器对象。
         *
         * @param config 一阶低通滤波器配置。
         */
        explicit LowPassFilter(const LowPassFilterConfig &config)
        {
            Init(config);
        }

        /**
         * @brief 初始化一阶低通滤波器。
         *
         * @param config 一阶低通滤波器配置。
         */
        void Init(const LowPassFilterConfig &config)
        {
            alpha_ = ClampAlpha(config.alpha);
            output_ = config.initial_output;
            initialized_ = true;
        }

        /**
         * @brief 重置滤波器输出值。
         *
         * @param output 重置后的输出值。
         */
        void Reset(float output = 0.0f)
        {
            output_ = output;
            initialized_ = true;
        }

        /**
         * @brief 执行一阶低通滤波。
         *
         * @param input 输入值。
         * @return 滤波后的输出值。
         */
        float Filter(float input)
        {
            if (!initialized_)
            {
                output_ = input;
                initialized_ = true;
                return output_;
            }

            output_ = alpha_ * input + (1.0f - alpha_) * output_;
            return output_;
        }

        /**
         * @brief 设置滤波系数。
         *
         * @param alpha 滤波系数，范围0到1。
         */
        void SetAlpha(float alpha)
        {
            alpha_ = ClampAlpha(alpha);
        }

        /**
         * @brief 获取当前输出值。
         *
         * @return 当前输出值。
         */
        float GetOutput() const
        {
            return output_;
        }

    private:
        float ClampAlpha(float alpha) const
        {
            if (alpha < 0.0f)
            {
                return 0.0f;
            }
            if (alpha > 1.0f)
            {
                return 1.0f;
            }
            return alpha;
        }

        float alpha_ = 1.0f;
        float output_ = 0.0f;
        bool initialized_ = false;
    };

    /**
     * @brief TD微分跟踪器。
     */
    class TDFilter
    {
    public:
        /**
         * @brief 构造TD微分跟踪器对象。
         */
        TDFilter() = default;

        /**
         * @brief 使用配置构造TD微分跟踪器对象。
         *
         * @param config TD微分跟踪器配置。
         */
        explicit TDFilter(const TDFilterConfig &config)
        {
            Init(config);
        }

        /**
         * @brief 初始化TD微分跟踪器。
         *
         * @param config TD微分跟踪器配置。
         */
        void Init(const TDFilterConfig &config)
        {
            r_ = config.r;
            h_ = config.h;
            v1_ = config.initial_v1;
            v2_ = config.initial_v2;
        }

        /**
         * @brief 重置TD状态变量。
         *
         * @param v1 跟踪信号初值。
         * @param v2 微分信号初值。
         */
        void Reset(float v1 = 0.0f, float v2 = 0.0f)
        {
            v1_ = v1;
            v2_ = v2;
        }

        /**
         * @brief 执行TD微分跟踪滤波。
         *
         * @param input 输入信号。
         * @return 跟踪信号。
         */
        float Filter(float input)
        {
            const float fh = -r_ * r_ * (v1_ - input) - 2.0f * r_ * v2_;
            v1_ += v2_ * h_;
            v2_ += fh * h_;
            return v1_;
        }

        /**
         * @brief 获取跟踪信号。
         *
         * @return 跟踪信号。
         */
        float GetTrackingValue() const
        {
            return v1_;
        }

        /**
         * @brief 获取微分信号。
         *
         * @return 微分信号。
         */
        float GetDifferentialValue() const
        {
            return v2_;
        }

        /**
         * @brief 设置速度因子。
         *
         * @param r 速度因子。
         */
        void SetR(float r)
        {
            r_ = r;
        }

        /**
         * @brief 设置积分步长。
         *
         * @param h 积分步长。
         */
        void SetH(float h)
        {
            h_ = h;
        }

    private:
        float r_ = 1.0f;
        float h_ = 0.001f;
        float v1_ = 0.0f;
        float v2_ = 0.0f;
    };

}

#endif // !FILTER_HPP
