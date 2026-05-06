#ifndef LED_HPP
#define LED_HPP

#include "drv_gpio.hpp"

namespace BSP::LED
{
    /**
     * @brief LED设备封装。
     */
    class Led
    {
    public:
        /**
         * @brief 构造LED对象。
         *
         * @param pin LED连接的GPIO引脚。
         * @param activeLow true表示低电平点亮，false表示高电平点亮。
         */
        Led(DRV::GPIO::IGpioPin &pin, bool activeLow = false)
            : pin_(pin), active_low_(activeLow)
        {
        }

        /**
         * @brief 点亮LED。
         */
        void On()
        {
            pin_.Write(active_low_ ? DRV::GPIO::PinLevel::Low
                                : DRV::GPIO::PinLevel::High);
        }

        /**
         * @brief 熄灭LED。
         */
        void Off()
        {
            pin_.Write(active_low_ ? DRV::GPIO::PinLevel::High
                                : DRV::GPIO::PinLevel::Low);
        }

        /**
         * @brief 翻转LED状态。
         */
        void Toggle()
        {
            pin_.Toggle();
        }

    private:
        DRV::GPIO::IGpioPin &pin_;
        bool active_low_;
    };
}

#endif // !LED_HPP
