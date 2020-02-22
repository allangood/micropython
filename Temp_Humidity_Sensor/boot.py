# This file is executed on every boot (including wake-boot from deepsleep)
import gc
import esp
esp.osdebug(None)
gc.enable()
#import uos, machine
#uos.dupterm(None, 1) # disable REPL on UART(0)
# import gc
# gc.collect()
#import webrepl
#webrepl.start()
