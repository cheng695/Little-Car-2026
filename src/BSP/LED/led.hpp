#ifndef LED_HPP
#define LED_HPP

#include "drv_gpio.hpp"

namespace BSP::LED
{
    class led
    {
    public:
        Led(DRV::GPIO::IGpioPin &pin, bool activeLow = false)
            : pin_(pin), active_low_(activeLow)
        {
        }

        void On()
        {
            pin_.Write(active_low_ ? DRV::GPIO::PinLevel::Low
                                : DRV::GPIO::PinLevel::High);
        }

        void Off()
        {
            pin_.Write(active_low_ ? DRV::GPIO::PinLevel::High
                                : DRV::GPIO::PinLevel::Low);
        }

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