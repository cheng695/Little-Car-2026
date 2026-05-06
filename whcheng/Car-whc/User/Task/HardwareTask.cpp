#include "LogTask.hpp"

#include "cmsis_os.h"

extern "C" void HardwareTask(void const *argument)
{
    for (;;) 
    {
        osDelay(1);
    }
}
