#ifndef DRV_UART_HPP
#define DRV_UART_HPP

#include <stdint.h>

namespace DRV::UART
{
    /**
     * @brief UART句柄逻辑通道标识。
     */
    enum class UartId : uint8_t
    {
        Debug = 0,
        Vision,
        Remote,
        Count
    };

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
         *
         * @return UartManager& 全局UART管理器实例。
         */
        static UartManager &Instance();

        /**
         * @brief 初始化UART管理器。
         */
        void Init();

        /**
         * @brief 注册HAL库相关的UART发送函数。
         *
         * @param function HAL库相关的UART发送函数。
         */
        void RegisterTxFunction(TxFunction function);

        /**
         * @brief 注册HAL库相关的UART接收启动函数。
         *
         * @param function HAL库相关的UART接收启动函数。
         */
        void RegisterRxFunction(RxFunction function);

        /**
         * @brief 注册指定UART句柄逻辑通道的接收回调函数。
         *
         * @param id UART句柄逻辑通道标识。
         * @param callback 该通道接收到原始数据后调用的回调函数。
         */
        void RegisterRxCallback(UartId id, RxCallback callback);

        /**
         * @brief 通过指定UART句柄逻辑通道发送原始数据。
         *
         * @param id UART句柄逻辑通道标识。
         * @param data 待发送的数据缓冲区。
         * @param len 待发送的数据长度，单位为字节。
         * @return true 数据已被平台发送函数接受。
         * @return false 参数无效或发送失败。
         */
        bool Send(UartId id, const uint8_t *data, uint16_t len);

        /**
         * @brief 通过指定UART句柄逻辑通道启动原始数据接收。
         *
         * @param id UART句柄逻辑通道标识。
         * @param buffer 接收缓冲区。
         * @param len 接收缓冲区长度，单位为字节。
         * @return true 接收启动成功。
         * @return false 参数无效或接收启动失败。
         */
        bool Receive(UartId id, uint8_t *buffer, uint16_t len);

        /**
         * @brief 通知UART管理器指定通道已有接收数据。
         *
         * @param id UART逻辑通道标识。
         * @param data 已接收的原始数据缓冲区。
         * @param len 已接收的数据长度，单位为字节。
         */
        void Callback(UartId id, const uint8_t *data, uint16_t len);

    private:
        static constexpr uint8_t kUartCount = static_cast<uint8_t>(UartId::Count);

        UartManager() = default;

        UartManager(const UartManager &) = delete;
        UartManager &operator=(const UartManager &) = delete;

        /**
         * @brief 获取UART句柄逻辑通道数量。
         *
         * @return uint8_t UART句柄逻辑通道数量。
         */
        static constexpr uint8_t UartCount()
        {
            return kUartCount;
        }

        /**
         * @brief 判断UART句柄逻辑通道标识是否有效。
         *
         * @param id UART句柄逻辑通道标识。
         * @return true 逻辑通道标识有效。
         * @return false 逻辑通道标识无效。
         */
        bool IsRealId(UartId id) const
        {
            return static_cast<uint8_t>(id) < UartCount();
        }

        /**
         * @brief 将UART句柄逻辑通道标识转换为数组下标。
         *
         * @param id UART句柄逻辑通道标识。
         * @return uint8_t 对应的数组下标。
         */
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
