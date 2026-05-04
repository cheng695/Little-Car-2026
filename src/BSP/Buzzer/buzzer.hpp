#ifndef BUZZER_HPP
#define BUZZER_HPP

#include <stdint.h>
#include "drv_gpio.hpp"
#include "stm32f1xx_hal.h"

namespace BSP::Buzzer
{
    /**
     * @brief 蜂鸣器设备封装。
     */
    class Buzzer
    {
    public:
        /**
         * @brief 构造蜂鸣器对象。
         *
         * @param pin 蜂鸣器连接的GPIO引脚。
         * @param activeLow true表示低电平响，false表示高电平响。
         */
        Buzzer(DRV::GPIO::IGpioPin &pin, bool activeLow = false)
            : pin_(pin), active_low_(activeLow)
        {
        }

        /**
         * @brief 打开蜂鸣器。
         */
        void On()
        {
            pin_.Write(active_low_ ? DRV::GPIO::PinLevel::Low
                                   : DRV::GPIO::PinLevel::High);
            is_on_ = true;
            timed_beep_active_ = false;
        }

        /**
         * @brief 关闭蜂鸣器。
         */
        void Off()
        {
            pin_.Write(active_low_ ? DRV::GPIO::PinLevel::High
                                   : DRV::GPIO::PinLevel::Low);
            is_on_ = false;
            timed_beep_active_ = false;
        }

        /**
         * @brief 翻转蜂鸣器状态。
         */
        void Toggle()
        {
            if (is_on_)
            {
                Off();
            }
            else
            {
                On();
            }
        }

        /**
         * @brief 触发一次定时蜂鸣，非阻塞。
         *
         * @param durationMs 蜂鸣持续时间，单位ms。
         */
        void Beep(uint32_t durationMs)
        {
            if (durationMs == 0)
            {
                Off();
                return;
            }

            pin_.Write(active_low_ ? DRV::GPIO::PinLevel::Low
                                   : DRV::GPIO::PinLevel::High);
            is_on_ = true;
            timed_beep_active_ = true;
            beep_end_tick_ = HAL_GetTick() + durationMs;
        }

        /**
         * @brief 更新蜂鸣器定时状态。
         *
         * @note 如果使用Beep()，需要在主循环或周期任务中调用该函数。
         */
        void Update()
        {
            if (!timed_beep_active_)
            {
                return;
            }

            if (static_cast<int32_t>(HAL_GetTick() - beep_end_tick_) >= 0)
            {
                Off();
            }
        }

        /**
         * @brief 获取蜂鸣器是否正在鸣叫。
         *
         * @return true 蜂鸣器正在鸣叫。
         * @return false 蜂鸣器未鸣叫。
         */
        bool IsOn() const
        {
            return is_on_;
        }

    private:
        DRV::GPIO::IGpioPin &pin_;
        bool active_low_;
        bool is_on_ = false;
        bool timed_beep_active_ = false;
        uint32_t beep_end_tick_ = 0;
    };
}

#endif // !BUZZR_HPP
