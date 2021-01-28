import machine
import gc
from wifi_manager import WifiManager

gc.collect()

wlan = WifiManager()

if wlan.check_connection():
    print("We're good to go!")
else:
    print("Something went wrong! Let's reboot and try again.")
    machine.reset()
    
gc.collect()