# WiFi Manager

WiFi Manager for ESP8266 and ESP32 using MicroPython. It might work in any other board since it only uses standard MicroPython libraries, but that's not tested.

![ESP8266](https://img.shields.io/badge/ESP-8266-000000.svg?longCache=true&style=flat&colorA=CC101F)
![ESP32](https://img.shields.io/badge/ESP-32-000000.svg?longCache=true&style=flat&colorA=CC101F)

## What's new?

Version 2.0 comes with some improvements:
- Better documentation (I hope);
- Some aesthetical changes in the code;
- Removal of unnecessary messages;
- Removal of the ability to set the ip address (to avoid unexpected problems);
- Option to reboot after network configuration (needs improvement);

## Wishlist

- [ ] Allow user to customize CSS;
- [ ] Custom fields for extra configuration (like mqtt server, etc)
- [ ] Turn this into a real python library with the option to be installed using pip;

## How It Works

- When your device starts up, it will try to connect to a previously saved wifi.
- If there is no saved network or if it fails to connect, it will start an access point;
- By connecting to the access point and going to the address 192.168.4.1 you be able to find your network and input the credentials;
- It will try to connect to the desired network, and if it's successful, it will save the credentials for future usage;
- Be aware that the wifi credentials will be saved in a plain text file, and this can be a security fault depending on your application;

## Installation and Usage

```python
# Download the "wifi_manager.py" file to your device;

# Import the library:
from wifi_manager import WiFiManager

# Initialize it
wm = WiFiManager()

# By default the SSID is WiFiManager and the password is wifimanager.
# You can customize the SSID and password of the AP for your needs:
wm = WiFiManager('my ssid', 'my password')

# Start the connection:
wm.connect()
```

## Methods

### .connect()

Tries to connect to a network and if it doesn't work start the configuration portal.

### .disconnect()

Disconnect from network.

### .is_connected()

Returns True if it's connected and False if it's not. It's the simpler way to test the connection inside your code.

### .get_address()

Returns a tuple with the network interface parameters: IP address, subnet mask, gateway and DNS server.

## Notes

- Do not use this library with other ones that works directly with the network interface, since it might have conflicts;
- If you want to enable the reboot after configuration, change the **self.reboot** parameter inside the *wifi_manager.py* file to **True**.

## Thanks To

https://github.com/tayfunulu/WiFiManager/
