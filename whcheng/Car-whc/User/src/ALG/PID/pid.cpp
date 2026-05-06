#include "pid.hpp"

#include <cmath>

namespace ALG::PID
{
    PID::PID(const PidConfig &config)
        : config_(config)
    {
    }

    void PID::SetConfig(const PidConfig &config)
    {
        config_ = config;
    }

    void PID::Reset()
    {
        td_value_ = 0.0f;
        td_derivative_ = 0.0f;
        integral_ = 0.0f;
        output_ = 0.0f;
        td_initialized_ = false;
    }

    float PID::Update(float target, float feedback)
    {
        if (config_.T <= 0.0f)
        {
            return output_;
        }

        const float error = target - feedback;

        /**  积分分离  */
        if (CanIntegrate(error))
        {
            integral_ += error * config_.T;
            /**  积分限幅  */
            ClampIntegral();
        }

        if (!td_initialized_)
        {
            InitTd(feedback);
        }

        /** 微分先行 + 滤波  */
        UpdateTd(feedback);

        /**  总输出  */
        output_ = CalculateOutput(error);
        ClampOutput();
        
        /** 积分抗饱和  */
        if(AntiWindup(error))
        {
            output_ = CalculateOutput(error);
            ClampOutput();
        }

        return output_;
    }

    float PID::GetOutput() const
    {
        return output_;
    }

    void PID::InitTd(float input)
    {
        td_value_ = input;
        td_derivative_ = 0.0f;
        td_initialized_ = true;
    }

    void PID::UpdateTd(float input)
    {
        if (config_.R <= 0.0f)
        {
            td_derivative_ = 0.0f;
            td_value_ = input;
            return;
        }

        const float fh = -config_.R * config_.R * (td_value_ - input)
                         - 2.0f * config_.R * td_derivative_;

        td_value_ += td_derivative_ * config_.T;
        td_derivative_ += fh * config_.T;
    }

    float PID::GetTdDerivative() const
    {
        return td_derivative_;
    }

    bool PID::CanIntegrate(float error) const
    {
        return config_.integral_separation_threshold <= 0.0f ||
               std::fabs(error) < config_.integral_separation_threshold;
    }

    void PID::ClampIntegral()
    {
        if (config_.integral_limit <= 0.0f)
        {
            return;
        }

        integral_ = std::clamp(
            integral_,
            -config_.integral_limit,
            config_.integral_limit
        );
    }

    void PID::ClampOutput()
    {
        if (config_.output_limit <= 0.0f)
        {
            return;
        }

        output_ = std::clamp(
            output_,
            -config_.output_limit,
            config_.output_limit
        );
    }

    bool PID::AntiWindup(float error)
    {
        if (config_.output_limit <= 0.0f)
        {
            return false;
        }

        const bool upper_saturated =
            output_ >= config_.output_limit && error > 0.0f;

        const bool lower_saturated =
            output_ <= -config_.output_limit && error < 0.0f;

        if (!upper_saturated && !lower_saturated)
        {
            return false;
        }

        integral_ -= error * config_.T;
        ClampIntegral();

        return true;
    }

    float PID::CalculateOutput(float error) const
    {
        return config_.kp * error
             + config_.ki * integral_
             - config_.kd * GetTdDerivative();
    }
}
