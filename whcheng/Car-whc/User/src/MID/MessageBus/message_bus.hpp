#ifndef MESSAGE_BUS_HPP
#define MESSAGE_BUS_HPP

#include <functional>
#include <stddef.h>
#include <vector>

namespace MID::MessageBus
{
    template <typename T>
    class MessageBus
    {
    public:
        using Subscriber = std::function<void(const T &)>;

        /**
         * @brief 获取消息总线单例。
         *
         * @return MessageBus& 消息总线实例。
         */
        static MessageBus &Instance()
        {
            static MessageBus instance;
            return instance;
        }

        /**
         * @brief 预留订阅者容量。
         *
         * @param count 预留的订阅者数量。
         */
        void Reserve(size_t count)
        {
            subscribers_.reserve(count);
        }

        /**
         * @brief 订阅消息。
         *
         * @param subscriber 消息回调函数。
         * @return true 订阅成功。
         * @return false 订阅失败，通常是回调函数为空。
         */
        bool Subscribe(Subscriber subscriber)
        {
            if (!subscriber)
            {
                return false;
            }

            subscribers_.push_back(subscriber);
            return true;
        }

        /**
         * @brief 发布消息。
         *
         * @param msg 待发布的消息。
         */
        void Publish(const T &msg)
        {
            for (auto &subscriber : subscribers_)
            {
                if (subscriber)
                {
                    subscriber(msg);
                }
            }
        }

        /**
         * @brief 清空所有订阅者。
         */
        void Clear()
        {
            subscribers_.clear();
        }

        /**
         * @brief 获取当前订阅者数量。
         *
         * @return size_t 当前订阅者数量。
         */
        size_t Size() const
        {
            return subscribers_.size();
        }

    private:
        MessageBus() = default;

        MessageBus(const MessageBus &) = delete;
        MessageBus &operator=(const MessageBus &) = delete;

        std::vector<Subscriber> subscribers_;
    };
}

#endif // !MESSAGE_BUS_HPP
