#ifndef DRV_GPIO_HPP
#define DRV_GPIO_HPP

#include <stdint.h>
#include "stm32f1xx_hal.h"

namespace DRV::GPIO
{
    /**
     * @brief GPIO引脚输出状态。
     */
    enum class PinState : uint8_t
    {
        Reset = 0,
        Set
    };

    /**
     * @brief GPIO引脚电平。
     */
    enum class PinLevel : uint8_t
    {
        Low = 0,
        High
    };

    /**
     * @brief GPIO引脚抽象接口。
     */
    class IGpioPin
    {
    public:
        virtual ~IGpioPin() = default;

        /**
         * @brief 写入GPIO引脚电平。
         *
         * @param level 目标电平。
         */
        virtual void Write(PinLevel level) = 0;

        /**
         * @brief 读取GPIO引脚电平。
         *
         * @return PinLevel 当前电平。
         */
        virtual PinLevel Read() const = 0;

        /**
         * @brief 翻转GPIO引脚电平。
         */
        virtual void Toggle() = 0;

        /**
         * @brief 设置GPIO引脚为高电平。
         */
        virtual void SetHigh() = 0;

        /**
         * @brief 设置GPIO引脚为低电平。
         */
        virtual void SetLow() = 0;
    };

    /**
     * @brief 基于STM32 HAL库的GPIO引脚实现。
     */
    class HalGpio : public IGpioPin
    {
    public:
        /**
         * @brief 构造HAL GPIO引脚对象。
         *
         * @param port GPIO端口。
         * @param pin GPIO引脚掩码。
         */
        HalGpio(GPIO_TypeDef *port, uint16_t pin)
            : port_(port), pin_(pin)
        {
        }

        /**
         * @brief 写入GPIO引脚电平。
         *
         * @param level 目标电平。
         */
        void Write(PinLevel level) override
        {
            if (port_ == nullptr)
            {
                return;
            }

            HAL_GPIO_WritePin(
                port_,
                pin_,
                level == PinLevel::High ? GPIO_PIN_SET : GPIO_PIN_RESET
            );
        }

        /**
         * @brief 读取GPIO引脚电平。
         *
         * @return PinLevel 当前电平，端口无效时返回低电平。
         */
        PinLevel Read() const override
        {
            if (port_ == nullptr)
            {
                return PinLevel::Low;
            }

            GPIO_PinState state = HAL_GPIO_ReadPin(port_, pin_);
            return state == GPIO_PIN_SET ? PinLevel::High : PinLevel::Low;
        }

        /**
         * @brief 翻转GPIO引脚电平。
         */
        void Toggle() override
        {
            if (port_ == nullptr)
            {
                return;
            }

            HAL_GPIO_TogglePin(port_, pin_);
        }

        /**
         * @brief 设置GPIO引脚为高电平。
         */
        void SetHigh() override
        {
            Write(PinLevel::High);
        }

        /**
         * @brief 设置GPIO引脚为低电平。
         */
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
