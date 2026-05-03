#ifndef DRV_GPIO_HPP
#define DRV_GPIO_HPP

namespace DRV::GPIO
{
    enum class PinState : uint8_t
    {
        Reset = 0,
        Set
    };

    enum class PinLevel : uint8_t
    {
        Low = 0,
        High
    };

    class IGpio
    {
    public:
        virtual ~IGpioPin() = default;

        virtual void Write(PinLevel level) = 0;
        virtual PinLevel Read() const = 0;
        virtual void Toggle() = 0;

        virtual void SetHigh() = 0;
        virtual void SetLow() = 0;
    };

    class Hal_Gpio : public IGpio
    {
    public:
        Hal_Gpio(GPIO_TypeDef *port, uint16_t pin)
            : port_(port), pin_(pin)
        {
        }

        void Write(PinLevel level) override
        {
            HAL_GPIO_WritePin(
                port_,
                pin_,
                level == PinLevel::High ? GPIO_PIN_SET : GPIO_PIN_RESET
            );
        }

        PinLevel Read() const override
        {
            GPIO_PinState state = HAL_GPIO_ReadPin(port_, pin_);
            return state == GPIO_PIN_SET ? PinLevel::High : PinLevel::Low;
        }

         void Toggle() override
        {
            HAL_GPIO_TogglePin(port_, pin_);
        }

        void SetHigh() override
        {
            Write(PinLevel::High);
        }

        void SetLow() override
        {
            Write(PinLevel::Low);
        }

    private:
        GPIO_TypeDef *port_;
        uint16_t pin_;
    };
}

#endif // !DRV_GPIO_HPP
