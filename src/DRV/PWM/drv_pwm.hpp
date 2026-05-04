#ifndef DRV_PWM_HPP
#define DRV_PWM_HPP

#include <stdint.h>
#include "stm32f1xx_hal.h"

namespace DRV::PWM
{
    /**
     * @brief PWM输出通道抽象接口。
     */
    class IPwm
    {
    public:
        virtual ~IPwm() = default;

        /**
         * @brief 启动PWM输出。
         *
         * @return true 启动成功。
         * @return false 启动失败。
         */
        virtual bool Start() = 0;

        /**
         * @brief 停止PWM输出。
         *
         * @return true 停止成功。
         * @return false 停止失败。
         */
        virtual bool Stop() = 0;

        /**
         * @brief 设置PWM比较值。
         *
         * @param compare 比较值，超过周期值时会被限制到周期值。
         * @return true 设置成功。
         * @return false 设置失败。
         */
        virtual bool SetCompare(uint32_t compare) = 0;

        /**
         * @brief 设置PWM占空比。
         *
         * @param duty 占空比，范围0~1000，对应0.0%~100.0%。
         * @return true 设置成功。
         * @return false 设置失败。
         */
        virtual bool SetDuty(uint16_t duty) = 0;

        /**
         * @brief 获取当前PWM比较值。
         *
         * @return uint32_t 当前比较值。
         */
        virtual uint32_t GetCompare() const = 0;

        /**
         * @brief 获取PWM周期值。
         *
         * @return uint32_t 自动重装载值。
         */
        virtual uint32_t GetPeriod() const = 0;
    };  

    /**
     * @brief 基于STM32 HAL库的PWM通道实现。
     */
    class HalPwmChannel : public IPwm
    {
    public:
        /**
         * @brief 构造HAL PWM通道对象。
         *
         * @param htim 定时器句柄。
         * @param channel PWM通道。
         */
        HalPwmChannel(TIM_HandleTypeDef *htim, uint32_t channel)
            : htim_(htim), channel_(channel)
        {
        }

        /**
         * @brief 启动PWM输出。
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

            return HAL_TIM_PWM_Start(htim_, channel_) == HAL_OK;
        }

        /**
         * @brief 停止PWM输出。
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

            return HAL_TIM_PWM_Stop(htim_, channel_) == HAL_OK;
        }

        /**
         * @brief 设置PWM比较值。
         *
         * @param compare 比较值，超过周期值时会自动限幅。
         * @return true 设置成功。
         * @return false 定时器无效。
         */
        bool SetCompare(uint32_t compare) override
        {
            if (htim_ == nullptr)
            {
                return false;
            }

            uint32_t period = GetPeriod();
            if (compare > period)
            {
                compare = period;
            }

            __HAL_TIM_SET_COMPARE(htim_, channel_, compare);
            
            return true;
        }

        /**
         * @brief 设置PWM占空比。
         *
         * @param duty 占空比，范围0~1000。
         * @return true 设置成功。
         * @return false 设置失败。
         */
        bool SetDuty(uint16_t duty) override
        {
            if (duty > 1000)
            {
                duty = 1000;
            }

            return SetCompare((GetPeriod() * static_cast<uint32_t>(duty)) / 1000U);
        }
        
        /**
         * @brief 获取当前PWM比较值。
         *
         * @return uint32_t 当前比较值，定时器无效时返回0。
         */
        uint32_t GetCompare() const override
        {
            if (htim_ == nullptr)
            {
                return 0;
            }

            return __HAL_TIM_GET_COMPARE(htim_, channel_);
        }

        /**
         * @brief 获取PWM周期值。
         *
         * @return uint32_t 自动重装载值，定时器无效时返回0。
         */
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
