#ifndef BUTTON_HPP
#define BUTTON_HPP

#include "drv_gpio.hpp"

namespace BSP::BUTTON
{
    /**
     * @brief 按键设备封装。
     */
    class Button
    {
    public:
        /**
         * @brief 构造按键对象。
         *
         * @param pin 按键连接的GPIO引脚。
         * @param activeLow true表示低电平按下，false表示高电平按下。
         */
        Button(DRV::GPIO::IGpioPin &pin, bool activeLow = true)
            : pin_(pin), active_low_(activeLow)
        {
        }

        /**
         * @brief 判断按键是否按下。
         *
         * @return true 按键已按下。
         * @return false 按键未按下。
         */
        bool IsPressed() const
        {
            auto level = pin_.Read();

            if (active_low_)
            {
                return level == DRV::GPIO::PinLevel::Low;
            }

            return level == DRV::GPIO::PinLevel::High;
        }

    private:
        DRV::GPIO::IGpioPin &pin_;
        bool active_low_;
    };
}

#endif // !BUTTON_HPP
