#ifndef DRV_UART_HPP
#define DRV_UART_HPP

#include <stdint.h>

#include "robot_uart.hpp"

namespace DRV::UART
{
    /**
     * @brief UART原始数据缓冲区。
     */
    struct UartData
    {
        const uint8_t *buffer;
        uint16_t size;
    };

    /**
     * @brief UART接收到原始数据后的回调函数类型。
     */
    using RxCallback = void (*)(UartId id, const UartData &data);

    /**
     * @brief UART发送函数类型。
     */
    using TxFunction = bool (*)(UartId id, const uint8_t *data, uint16_t len);

    /**
     * @brief UART接收启动函数类型。
     */
    using RxFunction = bool (*)(UartId id, uint8_t *buffer, uint16_t len);

    /**
     * @brief UART原始通道管理器。
     */
    class UartManager
    {
    public:
        /**
         * @brief 获取全局UART管理器实例。
         */
        static UartManager &Instance();

        /**
         * @brief 初始化UART管理器。
         */
        void Init();

        /**
         * @brief 注册UART发送函数。
         */
        void RegisterTxFunction(TxFunction function);

        /**
         * @brief 注册UART接收启动函数。
         */
        void RegisterRxFunction(RxFunction function);

        /**
         * @brief 注册指定逻辑UART的接收回调。
         */
        void RegisterRxCallback(UartId id, RxCallback callback);

        /**
         * @brief 通过指定UART发送原始数据。
         */
        bool Send(UartId id, const uint8_t *data, uint16_t len);

        /**
         * @brief 通过指定UART启动原始数据接收。
         */
        bool Receive(UartId id, uint8_t *buffer, uint16_t len);

        /**
         * @brief 通知UART管理器指定通道已有接收数据。
         */
        void Callback(UartId id, const uint8_t *data, uint16_t len);

    private:
        static constexpr uint8_t kUartCount = static_cast<uint8_t>(UartId::Count);

        UartManager() = default;

        UartManager(const UartManager &) = delete;
        UartManager &operator=(const UartManager &) = delete;

        static constexpr uint8_t UartCount()
        {
            return kUartCount;
        }

        bool IsRealId(UartId id) const
        {
            return static_cast<uint8_t>(id) < UartCount();
        }

        uint8_t ToIndex(UartId id) const
        {
            return static_cast<uint8_t>(id);
        }

        TxFunction tx_function_ = nullptr;
        RxFunction rx_function_ = nullptr;
        RxCallback rx_callbacks_[kUartCount] = {};
    };
}


#endif // !DRV_UART_HPP
