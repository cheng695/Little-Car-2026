#include "CommunicationTask.hpp"

#include "cmsis_os.h"

extern "C" void CommTask(void const *argument)
{
    for (;;) 
    {
        osDelay(1);
    }
}
