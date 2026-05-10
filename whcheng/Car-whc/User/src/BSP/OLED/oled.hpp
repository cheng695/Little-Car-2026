#ifndef OLED_HPP
#define OLED_HPP

#include <stddef.h>
#include <stdint.h>

#include "stm32f1xx_hal.h"

namespace BSP::OLED
{
    /**
     * @brief OLED像素颜色模式。
     */
    enum class Color : uint8_t
    {
        Black = 0,   // 熄灭像素。
        White = 1,   // 点亮像素。
        Inverse = 2, // 翻转像素当前状态。
    };

    /**
     * @brief 基于SSD1306控制器的128x64 I2C OLED封装。
     */
    class Oled
    {
    public:
        /**
         * @brief 屏幕宽度，单位为像素。
         */
        static constexpr uint8_t kWidth = 128;
        /**
         * @brief 屏幕高度，单位为像素。
         */
        static constexpr uint8_t kHeight = 64;
        /**
         * @brief SSD1306按8像素高分页，64像素高度对应8页。
         */
        static constexpr uint8_t kPages = kHeight / 8;
        /**
         * @brief 常见0.96寸I2C OLED的7位地址。
         */
        static constexpr uint8_t kDefaultAddress = 0x3C;

        /**
         * @brief 构造OLED对象。
         *
         * @param hi2c OLED连接的HAL I2C句柄。
         * @param address OLED的7位I2C地址。
         */
        explicit Oled(I2C_HandleTypeDef &hi2c, uint8_t address = kDefaultAddress);

        /**
         * @brief 初始化OLED控制器，并清屏刷新。
         *
         * @return true 初始化成功。
         * @return false 初始化失败。
         */
        bool Init();
        /**
         * @brief 检测OLED设备是否应答。
         *
         * @param timeout I2C检测超时时间，单位ms。
         * @return true 设备有应答。
         * @return false 设备无应答。
         */
        bool IsReady(uint32_t timeout = 10) const;
        /**
         * @brief 将显存内容刷新到OLED屏幕。
         *
         * @return true 刷新成功。
         * @return false 刷新失败。
         */
        bool Update();
        /**
         * @brief 填充整块显存，不会自动刷新。
         *
         * @param color 填充颜色。
         */
        void Fill(Color color);
        /**
         * @brief 清空屏幕并刷新。
         *
         * @return true 清屏成功。
         * @return false 清屏失败。
         */
        bool Clear();
        /**
         * @brief 设置后续字符输出的左上角坐标。
         *
         * @param x 横坐标，单位像素。
         * @param y 纵坐标，单位像素。
         */
        void SetCursor(uint8_t x, uint8_t y);
        /**
         * @brief 在显存中绘制单个像素，不会自动刷新。
         *
         * @param x 横坐标，单位像素。
         * @param y 纵坐标，单位像素。
         * @param color 像素颜色。
         */
        void DrawPixel(uint8_t x, uint8_t y, Color color);
        /**
         * @brief 写入一个6x8 ASCII字符到显存。
         *
         * @param ch 要写入的字符。
         * @param color 字符颜色。
         * @return true 写入成功。
         * @return false 写入失败。
         */
        bool WriteChar(char ch, Color color = Color::White);
        /**
         * @brief 写入ASCII字符串到显存。
         *
         * @param str 要写入的字符串。
         * @param color 字符颜色。
         * @return true 写入成功。
         * @return false 写入失败。
         */
        bool WriteString(const char *str, Color color = Color::White);
        /**
         * @brief 将有符号整数转换为字符串后写入显存。
         *
         * @param value 要写入的整数。
         * @param color 字符颜色。
         * @return true 写入成功。
         * @return false 写入失败。
         */
        bool WriteInt(int32_t value, Color color = Color::White);

    private:
        /**
         * @brief 发送SSD1306命令字节。
         *
         * @param command 命令字节。
         * @return true 发送成功。
         * @return false 发送失败。
         */
        bool WriteCommand(uint8_t command);
        /**
         * @brief 发送SSD1306显示数据。
         *
         * @param data 显示数据指针。
         * @param size 显示数据长度。
         * @return true 发送成功。
         * @return false 发送失败。
         */
        bool WriteData(const uint8_t *data, uint16_t size);
        /**
         * @brief 获取HAL I2C接口使用的左移后设备地址。
         *
         * @return 左移一位后的I2C设备地址。
         */
        uint16_t DeviceAddress() const;

        // HAL I2C 外设句柄。
        I2C_HandleTypeDef &hi2c_;
        // OLED 7 位 I2C 地址。
        uint8_t address_;
        // OLED 显存缓存：128 列 x 8 页。
        uint8_t buffer_[kWidth * kPages] = {};
        // 字符输出光标横坐标。
        uint8_t cursor_x_ = 0;
        // 字符输出光标纵坐标。
        uint8_t cursor_y_ = 0;
        // 初始化完成标志，避免未初始化时刷新。
        bool initialized_ = false;
    };
}

#endif
