#ifndef DRV_PWM_HPP
#define DRV_PWM_HPP 

namespace DRV::PWM
{
    class IPwm
    {
    public:
        virtual ~IPwm() = default;

        virtual bool Start() = 0;
        virtual bool Stop() = 0;

        virtual bool SetCompare(uint32_t compare) = 0;
        virtual bool SetDuty(uint16_t duty) = 0;

        virtual uint32_t GetCompare() const = 0;
        virtual uint32_t GetPeriod() const = 0;
    };  

    class HalPwmChannel : public IPwm
    {
    public:
          HalPwmChannel(TIM_HandleTypeDef *htim, uint32_t channel)
            : htim_(htim), channel_(channel)
        {
        }

        bool Star() override
        {
            return HAL_TIM_PWM_Start(htim_, channel_) == HAL_OK;
        }

        bool Stop() override
        {
            return HAL_TIM_PWM_Stop(htim_, channel_) == HAL_OK;
        }

        bool SetCompare(uint32_t compare) override
        {
            if(htim_ = nullptr)
            {
                return false;
            }

            uint32_t period = GetPeriod();
            if(compare > period)
            {
                compare = period;
            }

            __HAL_TIM_SET_COMPARE(htim_, channel_, compare);
            
            return true;
        }

        bool SetDuty(uint16_t duty) override
        {
            if(duty > 1000)
            {
                duty = 1000;
            }

            return SetCompare(static_cast<uint32_t>(duty * GetPeriod()));
        }
        
        uint32_t GetCompare() const override
        {
            if (htim_ == nullptr)
            {
                return 0;
            }

            return __HAL_TIM_GET_COMPARE(htim_, channel_);
        }

        uint32_t GetPeriod() const override
        {
            if (htim_ == nullptr)
            {
                return 0;
            }

            return __HAL_TIM_GET_AUTORELOAD(htim_);
        }

    private:
        TIM_HandleTypeDef *htim_;
        uint32_t channel_;    
    };
}

#endif // !DRV_PWM_HPP
