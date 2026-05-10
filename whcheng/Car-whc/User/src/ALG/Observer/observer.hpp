#ifndef OBSERVER_HPP
#define OBSERVER_HPP

namespace ALG::Observer
{
    /**
     * @brief UDE不确定性与扰动估计器配置。
     */
    struct UDEConfig
    {
        float a;
        float b;
        float initial_feedback;
    };

    /**
     * @brief UDE不确定性与扰动估计器。
     */
    class UDE
    {
    public:
        /**
         * @brief 构造UDE对象。
         */
        UDE() = default;

        /**
         * @brief 使用配置构造UDE对象。
         *
         * @param config UDE配置。
         */
        explicit UDE(const UDEConfig &config)
        {
            Init(config);
        }

        /**
         * @brief 初始化UDE观测器。
         *
         * @param config UDE配置。
         */
        void Init(const UDEConfig &config)
        {
            a_ = config.a;
            b_ = config.b;
            feedback_ = config.initial_feedback;
            output_ = 0.0f;
            x_dot_ = 0.0f;
            input_ = 0.0f;
        }

        /**
         * @brief 重置观测器状态。
         *
         * @param feedback 当前反馈状态。
         */
        void Reset(float feedback = 0.0f)
        {
            feedback_ = feedback;
            output_ = 0.0f;
            x_dot_ = 0.0f;
            input_ = 0.0f;
        }

        /**
         * @brief 更新UDE观测器。
         *
         * @param input 上一控制周期系统输入。
         * @param feedback 当前系统反馈状态。
         * @param x_dot 当前系统状态导数观测值。
         * @return 扰动补偿输出。
         */
        float Update(float input, float feedback, float x_dot)
        {
            input_ = input;
            feedback_ = feedback;
            x_dot_ = x_dot;

            if (b_ == 0.0f)
            {
                output_ = 0.0f;
            }
            else
            {
                output_ = (x_dot_ - a_ * feedback_ - b_ * input_) / b_;
            }

            return output_;
        }

        /**
         * @brief 获取扰动补偿输出。
         *
         * @return 扰动补偿输出。
         */
        float GetOutput() const
        {
            return output_;
        }

    private:
        float a_ = 0.0f;
        float b_ = 1.0f;
        float feedback_ = 0.0f;
        float output_ = 0.0f;
        float x_dot_ = 0.0f;
        float input_ = 0.0f;
    };
}

#endif // !OBSERVER_HPP
