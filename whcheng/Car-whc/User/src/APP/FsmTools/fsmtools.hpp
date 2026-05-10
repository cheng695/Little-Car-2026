#ifndef FSMTOOLS_HPP
#define FSMTOOLS_HPP

#include <stdint.h>

namespace APP::FsmTools
{
    /**
     * @brief 状态统计信息。
     */
    struct StateInfo
    {
        const char *name = "Unknown";
        uint32_t enter_count = 0;
        uint32_t total_run_time = 0;
        uint32_t current_run_time = 0;
        void *user_data = nullptr;
    };

    /**
     * @brief 通用有限状态机基础工具。
     *
     * @tparam State 状态枚举类型，建议使用enum class并以Count作为最后一个枚举值。
     * @tparam StateCount 状态数量。
     */
    template <typename State, uint8_t StateCount>
    class FsmBase
    {
    public:
        /**
         * @brief 初始化状态机。
         *
         * @param initial_state 初始状态。
         * @param state_names 状态名称数组，长度应等于StateCount。
         */
        void Init(State initial_state, const char *const *state_names)
        {
            for (uint8_t i = 0; i < StateCount; i++)
            {
                states_[i].name = state_names == nullptr ? "Unknown" : state_names[i];
                states_[i].enter_count = 0;
                states_[i].total_run_time = 0;
                states_[i].current_run_time = 0;
                states_[i].user_data = nullptr;
            }

            current_state_ = IsValid(initial_state) ? initial_state : State{};
            last_state_ = current_state_;
            initialized_ = true;
            states_[ToIndex(current_state_)].enter_count = 1;
        }

        /**
         * @brief 获取当前状态。
         *
         * @return 当前状态。
         */
        State GetState() const
        {
            return current_state_;
        }

        /**
         * @brief 获取上一个不同状态。
         *
         * @return 上一个不同状态。
         */
        State GetLastState() const
        {
            return last_state_;
        }

        /**
         * @brief 获取当前状态名称。
         *
         * @return 当前状态名称字符串。
         */
        const char *GetStateName() const
        {
            return GetStateName(current_state_);
        }

        /**
         * @brief 获取指定状态名称。
         *
         * @param state 指定状态。
         * @return 指定状态名称字符串。
         */
        const char *GetStateName(State state) const
        {
            if (!IsValid(state))
            {
                return "Invalid";
            }

            return states_[ToIndex(state)].name;
        }

        /**
         * @brief 获取指定状态总运行时间。
         *
         * @param state 指定状态。
         * @return 指定状态总运行时间，单位由Tick调用周期决定。
         */
        uint32_t GetStateRunTime(State state) const
        {
            if (!IsValid(state))
            {
                return 0;
            }

            const StateInfo &info = states_[ToIndex(state)];
            return info.total_run_time + info.current_run_time;
        }

        /**
         * @brief 获取当前状态已连续运行时间。
         *
         * @return 当前状态已连续运行时间，单位由Tick调用周期决定。
         */
        uint32_t GetCurrentStateRunTime() const
        {
            if (!initialized_)
            {
                return 0;
            }

            return states_[ToIndex(current_state_)].current_run_time;
        }

        /**
         * @brief 获取指定状态进入次数。
         *
         * @param state 指定状态。
         * @return 指定状态进入次数。
         */
        uint32_t GetStateEnterCount(State state) const
        {
            if (!IsValid(state))
            {
                return 0;
            }

            return states_[ToIndex(state)].enter_count;
        }

        /**
         * @brief 获取指定状态统计信息。
         *
         * @param state 指定状态。
         * @return 指定状态统计信息指针，状态非法时返回nullptr。
         */
        const StateInfo *GetStateInfo(State state) const
        {
            if (!IsValid(state))
            {
                return nullptr;
            }

            return &states_[ToIndex(state)];
        }

        /**
         * @brief 设置指定状态用户数据。
         *
         * @param state 指定状态。
         * @param user_data 用户数据指针。
         * @return true 设置成功。
         * @return false 设置失败。
         */
        bool SetUserData(State state, void *user_data)
        {
            if (!IsValid(state))
            {
                return false;
            }

            states_[ToIndex(state)].user_data = user_data;
            return true;
        }

        /**
         * @brief 获取指定状态用户数据。
         *
         * @param state 指定状态。
         * @return 用户数据指针，状态非法时返回nullptr。
         */
        void *GetUserData(State state) const
        {
            if (!IsValid(state))
            {
                return nullptr;
            }

            return states_[ToIndex(state)].user_data;
        }

        /**
         * @brief 状态机计时更新。
         *
         * @note 周期任务每调用一次，当前状态运行时间加1。
         */
        void Tick()
        {
            if (!initialized_)
            {
                return;
            }

            states_[ToIndex(current_state_)].current_run_time++;
        }

        /**
         * @brief 切换到指定状态。
         *
         * @param next_state 目标状态。
         * @return true 状态发生切换。
         * @return false 状态未切换或目标状态非法。
         */
        bool TransitionTo(State next_state)
        {
            if (!initialized_ || !IsValid(next_state) || next_state == current_state_)
            {
                return false;
            }

            StateInfo &old_info = states_[ToIndex(current_state_)];
            old_info.total_run_time += old_info.current_run_time;
            old_info.current_run_time = 0;

            last_state_ = current_state_;
            current_state_ = next_state;
            states_[ToIndex(current_state_)].enter_count++;
            return true;
        }

        /**
         * @brief 重置指定状态统计信息。
         *
         * @param state 指定状态。
         */
        void ResetStatistics(State state)
        {
            if (!IsValid(state))
            {
                return;
            }

            StateInfo &info = states_[ToIndex(state)];
            info.enter_count = state == current_state_ ? 1 : 0;
            info.total_run_time = 0;
            info.current_run_time = 0;
        }

        /**
         * @brief 重置所有状态统计信息。
         */
        void ResetAllStatistics()
        {
            for (uint8_t i = 0; i < StateCount; i++)
            {
                states_[i].enter_count = 0;
                states_[i].total_run_time = 0;
                states_[i].current_run_time = 0;
            }

            if (initialized_)
            {
                states_[ToIndex(current_state_)].enter_count = 1;
            }
        }

        /**
         * @brief 判断状态机是否已经初始化。
         *
         * @return true 已初始化。
         * @return false 未初始化。
         */
        bool IsInitialized() const
        {
            return initialized_;
        }

    protected:
        /**
         * @brief 判断状态是否合法。
         *
         * @param state 指定状态。
         * @return true 状态合法。
         * @return false 状态非法。
         */
        bool IsValid(State state) const
        {
            return ToIndex(state) < StateCount;
        }

        /**
         * @brief 将状态枚举转换为数组索引。
         *
         * @param state 指定状态。
         * @return 状态数组索引。
         */
        uint8_t ToIndex(State state) const
        {
            return static_cast<uint8_t>(state);
        }

    private:
        State current_state_{};
        State last_state_{};
        StateInfo states_[StateCount] = {};
        bool initialized_ = false;
    };
}

#endif // !FSMTOOLS_HPP
