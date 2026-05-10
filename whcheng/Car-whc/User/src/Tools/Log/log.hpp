#ifndef LOG_HPP
#define LOG_HPP

#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "drv_uart.hpp"
#include "stm32f1xx_hal.h"

#ifndef LOG_ENABLE_RTT
#define LOG_ENABLE_RTT 0
#endif

#if LOG_ENABLE_RTT
#include "SEGGER_RTT.h"
#endif

namespace Tools::Log
{
    /**
     * @brief 日志等级。
     */
    enum class Level : uint8_t
    {
        Debug = 0,
        Info,
        Warn,
        Error,
        None,
    };

    /**
     * @brief 日志输出后端。
     */
    enum class Backend : uint8_t
    {
        Uart = 0,
        Rtt,
        Both,
    };

    /**
     * @brief 日志配置。
     */
    struct Config
    {
        Backend backend = Backend::Uart;
        DRV::UART::UartId uart_id = DRV::UART::UartId::Debug;
        uint8_t rtt_buffer_index = 0;
        Level min_level = Level::Debug;
        bool enable_timestamp = true;
        bool enable_level_tag = true;
        bool enable_newline = true;
    };

    /**
     * @brief 轻量级UART日志器。
     */
    class Logger
    {
    public:
        /**
         * @brief 获取全局日志器实例。
         *
         * @return 全局日志器引用。
         */
        static Logger &Instance()
        {
            static Logger logger;
            return logger;
        }

        /**
         * @brief 初始化日志器。
         *
         * @param config 日志配置。
         */
        void Init(const Config &config)
        {
            config_ = config;
            initialized_ = true;
        }

        /**
         * @brief 设置最小输出日志等级。
         *
         * @param level 最小日志等级。
         */
        void SetMinLevel(Level level)
        {
            config_.min_level = level;
        }

        /**
         * @brief 获取最小输出日志等级。
         *
         * @return 最小日志等级。
         */
        Level GetMinLevel() const
        {
            return config_.min_level;
        }

        /**
         * @brief 输出格式化日志。
         *
         * @param level 日志等级。
         * @param format printf风格格式字符串。
         * @return true 输出成功。
         * @return false 输出失败。
         */
        bool Printf(Level level, const char *format, ...)
        {
            va_list args;
            va_start(args, format);
            const bool result = VPrintf(level, format, args);
            va_end(args);
            return result;
        }

        /**
         * @brief 输出格式化日志。
         *
         * @param level 日志等级。
         * @param format printf风格格式字符串。
         * @param args 可变参数列表。
         * @return true 输出成功。
         * @return false 输出失败。
         */
        bool VPrintf(Level level, const char *format, va_list args)
        {
            if (!ShouldOutput(level) || format == nullptr)
            {
                return false;
            }

            char buffer[kBufferSize] = {};
            int offset = 0;

            if (config_.enable_timestamp)
            {
                offset += SafeSnprintf(
                    buffer + offset,
                    BufferRemain(offset),
                    "[%lu] ",
                    static_cast<unsigned long>(HAL_GetTick())
                );
            }

            if (config_.enable_level_tag)
            {
                offset += SafeSnprintf(
                    buffer + offset,
                    BufferRemain(offset),
                    "[%s] ",
                    LevelName(level)
                );
            }

            offset += SafeVsnprintf(buffer + offset, BufferRemain(offset), format, args);

            if (config_.enable_newline)
            {
                offset += SafeSnprintf(buffer + offset, BufferRemain(offset), "\r\n");
            }

            return Send(buffer, offset);
        }

        /**
         * @brief 输出原始字符串。
         *
         * @param level 日志等级。
         * @param text 字符串。
         * @return true 输出成功。
         * @return false 输出失败。
         */
        bool Write(Level level, const char *text)
        {
            if (!ShouldOutput(level) || text == nullptr)
            {
                return false;
            }

            return Send(text, static_cast<int>(strlen(text)));
        }

    private:
        static constexpr int kBufferSize = 160;

        Logger() = default;

        Logger(const Logger &) = delete;
        Logger &operator=(const Logger &) = delete;

        bool ShouldOutput(Level level) const
        {
            if (!initialized_ || config_.min_level == Level::None)
            {
                return false;
            }

            return static_cast<uint8_t>(level) >= static_cast<uint8_t>(config_.min_level);
        }

        const char *LevelName(Level level) const
        {
            switch (level)
            {
                case Level::Debug:
                    return "DEBUG";
                case Level::Info:
                    return "INFO";
                case Level::Warn:
                    return "WARN";
                case Level::Error:
                    return "ERROR";
                default:
                    return "NONE";
            }
        }

        int BufferRemain(int offset) const
        {
            if (offset >= kBufferSize)
            {
                return 0;
            }

            return kBufferSize - offset;
        }

        int SafeSnprintf(char *buffer, int size, const char *format, ...)
        {
            if (buffer == nullptr || size <= 0 || format == nullptr)
            {
                return 0;
            }

            va_list args;
            va_start(args, format);
            const int written = SafeVsnprintf(buffer, size, format, args);
            va_end(args);
            return written;
        }

        int SafeVsnprintf(char *buffer, int size, const char *format, va_list args)
        {
            if (buffer == nullptr || size <= 0 || format == nullptr)
            {
                return 0;
            }

            const int written = vsnprintf(buffer, static_cast<size_t>(size), format, args);
            if (written < 0)
            {
                buffer[0] = '\0';
                return 0;
            }

            if (written >= size)
            {
                return size - 1;
            }

            return written;
        }

        bool Send(const char *data, int len)
        {
            if (data == nullptr || len <= 0)
            {
                return false;
            }

            bool result = false;

            if (config_.backend == Backend::Uart || config_.backend == Backend::Both)
            {
                result = DRV::UART::UartManager::Instance().Send(
                    config_.uart_id,
                    reinterpret_cast<const uint8_t *>(data),
                    static_cast<uint16_t>(len)
                ) || result;
            }

            if (config_.backend == Backend::Rtt || config_.backend == Backend::Both)
            {
                result = SendRtt(data, len) || result;
            }

            return result;
        }

        bool SendRtt(const char *data, int len)
        {
#if LOG_ENABLE_RTT
            return SEGGER_RTT_Write(
                config_.rtt_buffer_index,
                data,
                static_cast<unsigned>(len)
            ) >= 0;
#else
            (void)data;
            (void)len;
            return false;
#endif
        }

        Config config_{};
        bool initialized_ = false;
    };
}

#define LOG_DEBUG(format, ...) \
    Tools::Log::Logger::Instance().Printf(Tools::Log::Level::Debug, format, ##__VA_ARGS__)

#define LOG_INFO(format, ...) \
    Tools::Log::Logger::Instance().Printf(Tools::Log::Level::Info, format, ##__VA_ARGS__)

#define LOG_WARN(format, ...) \
    Tools::Log::Logger::Instance().Printf(Tools::Log::Level::Warn, format, ##__VA_ARGS__)

#define LOG_ERROR(format, ...) \
    Tools::Log::Logger::Instance().Printf(Tools::Log::Level::Error, format, ##__VA_ARGS__)

#endif // !LOG_HPP
