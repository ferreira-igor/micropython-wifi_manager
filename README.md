# MicroPython WiFi Manager

<b>Warnings:</b>

- It was only tested using the MicroPython v1.13 and the ESP8266 and ESP32 from Wemos boards.
- Your ssid and password information will be saved in plain text file (wifi.dat) in your ESP module for future usage. Be careful about security!

<b>Description:</b>

An updated and optimized wifi manager library for ESP chips. The code is based on this work: https://github.com/tayfunulu/WiFiManager/.
The main goal was to update the code, fix some bugs, optimize it and reduce the memory usage.

<b>Usage:</b>

- Upload wifi_manager.py to ESP;
- Import the library using "from wifi_manager import WifiManager";
- Create the object using wlan = WifiManager("AP SSID", "AP PASSWORD"). The default values are SSID: WifiManager and PASSWORD: wifimanager;
- Start the library using wlan.check_connection(). If the connection is successful, the function will return true, otherwise it will return false;

An usage example can be found in boot.py. There is no need to call this function more then once, so I suggest to call at boot process.

