#include "drv_uart.hpp"

namespace DRV::UART
{
    UartManager &UartManager::Instance()
    {
        static UartManager instance;
        return instance;
    }

    void UartManager::Init()
    {
        tx_function_ = nullptr;
        rx_function_ = nullptr;

        for (uint8_t i = 0; i < UartCount(); i++) 
        {
            rx_callbacks_[i] = nullptr;
        }
    }

    void UartManager::RegisterTxFunction(TxFunction function)
    {
        tx_function_ = function;
    }

    void UartManager::RegisterRxFunction(RxFunction function)
    {
        rx_function_ = function;
    }

    void UartManager::RegisterRxCallback(UartId id, RxCallback callback)
    {
        if (!IsRealId(id)) 
        {
            return;
        }

        rx_callbacks_[ToIndex(id)] = callback;
    }

    bool UartManager::Send(UartId id, const uint8_t *data, uint16_t len)
    {
        if (!IsRealId(id) || tx_function_ == nullptr) 
        {
            return false;
        }

        if (data == nullptr || len == 0) 
        {
            return false;
        }

        return tx_function_(id, data, len);
    }

    bool UartManager::Receive(UartId id, uint8_t *buffer, uint16_t len)
    {
        if (!IsRealId(id) || rx_function_ == nullptr) 
        {
            return false;
        }

        if (buffer == nullptr || len == 0) 
        {
            return false;
        }

        return rx_function_(id, buffer, len);
    }

    void UartManager::Callback(UartId id, const uint8_t *data, uint16_t len)
    {
        if (!IsRealId(id) || data == nullptr || len == 0) 
        {
            return;
        }

        RxCallback callback = rx_callbacks_[ToIndex(id)];
        if (callback == nullptr) 
        {
            return;
        }

        UartData uart_data{data, len};
        callback(id, uart_data);
    }
}
