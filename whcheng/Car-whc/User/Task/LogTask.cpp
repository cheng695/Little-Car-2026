#include "LogTask.hpp"

#include "cmsis_os.h"

extern "C" void LogTask(void const *argument)
{
    for (;;) 
    {
        osDelay(1);
    }
}
