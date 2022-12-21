# Author: Igor Ferreira
# License: MIT
# Version: 2.0.1
# Description: WiFi Manager for ESP8266 and ESP32 using MicroPython.

# AP Connection leads to server IP of http://192.168.4.1/ for configuration

import machine
import network
import usocket
import ure
import utime

import cryptolib
import ubinascii

class WifiManager:
    SECRET_KEY = "somesecret"  # Modify this code to 'personalize' the key...
    DELIMITER = ',' # Should be a char that does NOT appear in Base64 ..
    
    def __init__(self, ssid = 'WifiManager', password = 'wifimanager'):
        self.wlan_sta = network.WLAN(network.STA_IF)
        self.wlan_sta.active(True)
        self.wlan_ap = network.WLAN(network.AP_IF)

        # Avoids simple mistakes with wifi ssid and password lengths, but doesn't check for forbidden or unsupported characters.
        if len(ssid) > 32:
            raise Exception('The SSID cannot be longer than 32 characters.')
        else:
            self.ap_ssid = ssid
        if len(password) < 8:
            raise Exception('The password cannot be less than 8 characters long.')
        else:
            self.ap_password = password

        secret = WifiManager.SECRET_KEY
        secret = secret + "X" * (32-len(secret)%32) # Padding the secret to make 32 multiple
        
        self.crypto_encr = cryptolib.aes(bytes(secret, 'utf-8'), 1)
        self.crypto_decr = cryptolib.aes(bytes(secret, 'utf-8'), 1) # an instance can be used either for encryption / decryption ...
        
        # Set the access point authentication mode to WPA2-PSK.
        self.ap_authmode = 3

        # The file where the credentials will be stored.
        self.sta_profiles = 'wifi.dat'

        # Prevents the device from automatically trying to connect to the last saved network without first going through the steps defined in the code.
        self.wlan_sta.disconnect()

        # Change to True if you want the device to reboot after configuration.
        # Useful if you're having problems with web server applications after WiFi configuration.
        self.reboot = False

    def pad_password(self, password):
        return password + " "*(16 - len(password)%16)
    
    def unpad_password(self, password):
        return password.strip()
    

    def connect(self):
        if self.wlan_sta.isconnected():
            return
        profiles = self.__ReadProfiles()
        for ssid, *_ in self.wlan_sta.scan():
            ssid = ssid.decode("utf-8")
            if ssid in profiles:
                password = profiles[ssid]
                if self.__WifiConnect(ssid, password):
                    return
        print('Could not connect to any WiFi network. Starting the configuration portal...')
        self.__WebServer()


    def disconnect(self):
        if self.wlan_sta.isconnected():
            self.wlan_sta.disconnect()


    def is_connected(self):
        return self.wlan_sta.isconnected()


    def get_address(self):
        return self.wlan_sta.ifconfig()


    def __WriteProfiles(self, profiles):
        lines = []
        for ssid, password in profiles.items():
            try:
                lines.append('{0}{1}{2}'.format(ssid, WifiManager.DELIMITER, ubinascii.b2a_base64(self.crypto_encr.encrypt(self.pad_password(password))).decode() ))
            except Exception as e:
                print(e)
            
        with open(self.sta_profiles, 'w') as myfile:
            myfile.write('\n'.join(lines))


    def __ReadProfiles(self):
        try:
            with open(self.sta_profiles) as myfile:
                lines = myfile.readlines()
            print("Found {0} entries in file\n".format(len(lines)))
        except OSError:
            lines = []
            pass
        
        profiles = {}
        for line in lines:
            ssid, password = line.strip().split(WifiManager.DELIMITER)
            try:
                profiles[ssid] = self.unpad_password(self.crypto_decr.decrypt(ubinascii.a2b_base64(password)).decode())
            except Exception as e:
                print(e)
        return profiles


    def __WifiConnect(self, ssid, password):
        print('Trying to connect to:', ssid)
        self.wlan_sta.connect(ssid, password)
        for _ in range(100):
            if self.wlan_sta.isconnected():
                print('\nConnected! Network information:', self.wlan_sta.ifconfig())
                return True
            else:
                print('.', end='')
                utime.sleep_ms(100)
        print('\nConnection failed!')
        self.wlan_sta.disconnect()
        return False


    def __WebServer(self):
        self.wlan_ap.active(True)
        self.wlan_ap.config(essid = self.ap_ssid, password = self.ap_password, authmode = self.ap_authmode)
        server_socket = usocket.socket()
        server_socket.close()
        server_socket = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
        server_socket.setsockopt(usocket.SOL_SOCKET, usocket.SO_REUSEADDR, 1)
        server_socket.bind(('', 80))
        server_socket.listen(1)
        print('Connect to', self.ap_ssid, 'with the password', self.ap_password, 'and access the captive portal at', self.wlan_ap.ifconfig()[0])
        while True:
            if self.wlan_sta.isconnected():
                self.wlan_ap.active(False)
                if self.reboot:
                    print('The device will reboot in 5 seconds.')
                    utime.sleep(5)
                    machine.reset()
                return
            self.client, addr = server_socket.accept()
            try:
                self.client.settimeout(5.0)
                self.request = b''
                try:
                    while True:
                        if '\r\n\r\n' in self.request:
                            # Fix for Safari browser
                            self.request += self.client.recv(512)
                            break
                        self.request += self.client.recv(128)
                except OSError:
                    # It's normal to receive timeout errors in this stage, we can safely ignore them.
                    pass
                if self.request:
                    url = ure.search('(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP', self.request).group(1).decode('utf-8').rstrip('/')
                    if url == '':
                        self.__HandleRoot()
                    elif url == 'configure':
                        self.__HandleConfigure()
                    else:
                        self.__HandleNotFound()
            except Exception:
                print('Something went wrong! Reboot and try again.')
                return
            finally:
                self.client.close()


    def __SendHeader(self, status_code = 200):
        self.client.send("""HTTP/1.1 {0} OK\r\n""".format(status_code))
        self.client.send("""Content-Type: text/html\r\n""")
        self.client.send("""Connection: close\r\n""")


    def __SendResponse(self, payload, status_code = 200):
        self.__SendHeader(status_code)
        self.client.sendall("""
            <!DOCTYPE html>
            <html lang="en">
                <head>
                    <title>WiFi Manager</title>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <link rel="icon" href="data:,">
                </head>
                <body>
                    {0}
                </body>
            </html>
        """.format(payload))
        self.client.close()


    def __HandleRoot(self):
        self.__SendHeader()
        self.client.sendall("""
            <!DOCTYPE html>
            <html lang="en">
                <head>
                    <title>WiFi Manager</title>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <link rel="icon" href="data:,">
                </head>
                <body>
                    <h1>{0}</h1>
                    <form action="/configure" method="post" accept-charset="utf-8">
        """.format(self.ap_ssid))
        for ssid, *_ in self.wlan_sta.scan():
            ssid = ssid.decode("utf-8")
            self.client.sendall("""
                        <p><input type="radio" name="ssid" value="{0}" id="{0}"><label for="{0}">&nbsp;{0}</label></p>
            """.format(ssid))
        self.client.sendall("""
                        <p><label for="password">Password:&nbsp;</label><input type="password" id="password" name="password"></p>
                        <p><input type="submit" value="Connect"></p>
                    </form>
                </body>
            </html>
        """)
        self.client.close()


    def __HandleConfigure(self):
        match = ure.search('ssid=([^&]*)&password=(.*)', self.request)
        if match:
            ssid = match.group(1).decode('utf-8').replace('%3F', '?').replace('%21', '!').replace('%23', '#')
            password = match.group(2).decode('utf-8').replace('%3F', '?').replace('%21', '!')
            if len(ssid) == 0:
                self.__SendResponse("""<p>SSID must be provided!</p><p>Go back and try again!</p>""", 400)
            elif self.__WifiConnect(ssid, password):
                self.__SendResponse("""<p>Successfully connected to</p><h1>{0}</h1><p>IP address: {1}</p>""".format(ssid, self.wlan_sta.ifconfig()[0]))
                profiles = self.__ReadProfiles()
                profiles[ssid] = password
                self.__WriteProfiles(profiles)
                utime.sleep(5)
            else:
                self.__SendResponse("""<p>Could not connect to</p><h1>{0}</h1><p>Go back and try again!</p>""".format(ssid))
                utime.sleep(5)
        else:
            self.__SendResponse("""<p>Parameters not found!</p>""", 400)
            utime.sleep(5)


    def __HandleNotFound(self):
        self.__SendResponse("""<p>Path not found!</p>""", 404)
        utime.sleep(5)
