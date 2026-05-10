#ifndef FEEDFORWARD_HPP
#define FEEDFORWARD_HPP

#include <math.h>

namespace ALG::Feedforward
{
    struct AccelerationFeedforwardConfig
    {
        float k_acc;
        float control_cycle;
        float initial_target;
    };

    struct VelocityFeedforwardConfig
    {
        float k_vel;
        float control_cycle;
        float initial_target;
    };

    struct GravityFeedforwardConfig
    {
        float k_gravity;
        float phi_deg;
    };

    struct FrictionFeedforwardConfig
    {
        float friction_value;
    };

    struct GimbalFullCompensationConfig
    {
        float k_j;
        float control_dt;
        float viscous_friction;
        float coulomb_friction;
        float deadzone;
        float acc_filter_alpha;
    };

    class AccelerationFeedforward
    {
    public:
        AccelerationFeedforward() = default;

        explicit AccelerationFeedforward(const AccelerationFeedforwardConfig &config)
        {
            Init(config);
        }

        void Init(const AccelerationFeedforwardConfig &config)
        {
            k_acc_ = config.k_acc;
            control_cycle_ = config.control_cycle;
            last_target_ = config.initial_target;
            acceleration_ = 0.0f;
            output_ = 0.0f;
        }

        float Update(float target)
        {
            if (control_cycle_ <= 0.0f)
            {
                output_ = 0.0f;
                return output_;
            }

            acceleration_ = (target - last_target_) / control_cycle_;
            output_ = k_acc_ * acceleration_;
            last_target_ = target;
            return output_;
        }

        float GetOutput() const
        {
            return output_;
        }

    private:
        float k_acc_ = 0.0f;
        float control_cycle_ = 0.001f;
        float last_target_ = 0.0f;
        float acceleration_ = 0.0f;
        float output_ = 0.0f;
    };

    class VelocityFeedforward
    {
    public:
        VelocityFeedforward() = default;

        explicit VelocityFeedforward(const VelocityFeedforwardConfig &config)
        {
            Init(config);
        }

        void Init(const VelocityFeedforwardConfig &config)
        {
            k_vel_ = config.k_vel;
            control_cycle_ = config.control_cycle;
            last_target_ = config.initial_target;
            velocity_ = 0.0f;
            output_ = 0.0f;
        }

        float Update(float target)
        {
            if (control_cycle_ <= 0.0f)
            {
                output_ = 0.0f;
                return output_;
            }

            velocity_ = (target - last_target_) / control_cycle_;
            output_ = k_vel_ * velocity_;
            last_target_ = target;
            return output_;
        }

        float GetOutput() const
        {
            return output_;
        }

    private:
        float k_vel_ = 0.0f;
        float control_cycle_ = 0.001f;
        float last_target_ = 0.0f;
        float velocity_ = 0.0f;
        float output_ = 0.0f;
    };

    class GravityFeedforward
    {
    public:
        GravityFeedforward() = default;

        explicit GravityFeedforward(const GravityFeedforwardConfig &config)
        {
            Init(config);
        }

        void Init(const GravityFeedforwardConfig &config)
        {
            k_gravity_ = config.k_gravity;
            phi_deg_ = config.phi_deg;
            output_ = 0.0f;
        }

        float Update(float theta_deg)
        {
            static constexpr float kDegToRad = 3.14159265358979323846f / 180.0f;
            output_ = k_gravity_ * cosf((theta_deg + phi_deg_) * kDegToRad);
            return output_;
        }

        float GetOutput() const
        {
            return output_;
        }

    private:
        float k_gravity_ = 0.0f;
        float phi_deg_ = 0.0f;
        float output_ = 0.0f;
    };

    class FrictionFeedforward
    {
    public:
        FrictionFeedforward() = default;

        explicit FrictionFeedforward(const FrictionFeedforwardConfig &config)
        {
            Init(config);
        }

        void Init(const FrictionFeedforwardConfig &config)
        {
            friction_value_ = config.friction_value;
            output_ = 0.0f;
        }

        float Update(float target)
        {
            if (target > 0.0f)
            {
                output_ = friction_value_;
            }
            else if (target < 0.0f)
            {
                output_ = -friction_value_;
            }
            else
            {
                output_ = 0.0f;
            }
            return output_;
        }

        float GetOutput() const
        {
            return output_;
        }

    private:
        float friction_value_ = 0.0f;
        float output_ = 0.0f;
    };

    class GimbalFullCompensation
    {
    public:
        GimbalFullCompensation() = default;

        explicit GimbalFullCompensation(const GimbalFullCompensationConfig &config)
        {
            Init(config);
        }

        void Init(const GimbalFullCompensationConfig &config)
        {
            k_j_ = config.k_j;
            control_dt_ = config.control_dt;
            viscous_friction_ = config.viscous_friction;
            coulomb_friction_ = config.coulomb_friction;
            deadzone_ = config.deadzone;
            acc_filter_alpha_ = ClampAlpha(config.acc_filter_alpha);
            torque_ = 0.0f;
            friction_ = 0.0f;
            acc_feedforward_ = 0.0f;
            last_ref_velocity_ = 0.0f;
            filtered_acc_ = 0.0f;
        }

        float Update(float feedback_velocity, float ref_velocity)
        {
            float sign = 0.0f;
            if (deadzone_ > 0.0f)
            {
                if (feedback_velocity > deadzone_)
                {
                    sign = 1.0f;
                }
                else if (feedback_velocity < -deadzone_)
                {
                    sign = -1.0f;
                }
                else
                {
                    sign = feedback_velocity / deadzone_;
                }
            }

            friction_ = viscous_friction_ * feedback_velocity + sign * coulomb_friction_;

            float ref_acc_raw = 0.0f;
            if (control_dt_ > 0.0f)
            {
                ref_acc_raw = (ref_velocity - last_ref_velocity_) / control_dt_;
            }
            last_ref_velocity_ = ref_velocity;

            filtered_acc_ = filtered_acc_ * (1.0f - acc_filter_alpha_) + ref_acc_raw * acc_filter_alpha_;
            acc_feedforward_ = k_j_ * filtered_acc_;
            torque_ = friction_ + acc_feedforward_;
            return torque_;
        }

        float GetTorque() const
        {
            return torque_;
        }

        float GetFriction() const
        {
            return friction_;
        }

        float GetAccFeedforward() const
        {
            return acc_feedforward_;
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

        float k_j_ = 0.0f;
        float control_dt_ = 0.001f;
        float viscous_friction_ = 0.0f;
        float coulomb_friction_ = 0.0f;
        float deadzone_ = 3.0f;
        float acc_filter_alpha_ = 0.15f;
        float torque_ = 0.0f;
        float friction_ = 0.0f;
        float acc_feedforward_ = 0.0f;
        float last_ref_velocity_ = 0.0f;
        float filtered_acc_ = 0.0f;
    };
}

#endif // !FEEDFORWARD_HPP
