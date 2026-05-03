#ifndef BUTTON_HPP
#define BUTTON_HPP

#include "drv_gpio.hpp"

namespace BSP::BUTTON
{
    class Button
    {
    public:
        Button(DRV::GPIO::IGpioPin &pin, bool activeLow = true)
            : pin_(pin), active_low_(activeLow)
        {
        }

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
