# Project: WiFi Manager
# Author: Igor Ferreira
# Description: An updated and optimized wifi manager library for ESP chips, written in MicroPython.
# Source: https://github.com/h1pn0z/micropython-wifi_manager/

import network
import ure
try:
    import usocket as socket
except:
    import socket
try:
    import utime as time
except:
    import time


class WifiManager:

    def __init__(self, ssid = "WifiManager", password = "wifimanager", ip = None):
        self.wlan_sta = network.WLAN(network.STA_IF)
        self.wlan_sta.active(True)
        self.wlan_ap = network.WLAN(network.AP_IF)
        self.ap_ssid = ssid
        if len(password) < 8:
            raise Exception("Your password must be at least 8 characters long.")
        else:
            self.ap_password = password
        self.ap_ip = ip
        # Sets the wifi authentication mode to WPA2-PSK.
        self.ap_authmode = 3
        self.sta_profiles = "wifi.dat"
        # Forces a new scan and connection to avoid problems with ESP trying to automatically connect to the last used network.
        self.wlan_sta.disconnect()

    def check_connection(self):
        # If it's already connected, why to connect again?
        if self.wlan_sta.isconnected():
            return True
        # Here we read the previous saved credentials and make a scan, if a network name matches, we try to connect to it.
        profiles = self.read_profiles()
        for ssid, *_ in self.wlan_sta.scan():
            ssid = ssid.decode("utf-8")
            if ssid in profiles:
                password = profiles[ssid]
                if self.wifi_connect(ssid, password):
                    return True
                else:
                    print("It didn't work, let's try the next one!")
            else:
                print("Skipping unknown network:", ssid)
        # And if it fails to connect we start the captive portal.
        print("Could not connect to any WiFi network. Starting the captive portal...")
        return self.web_server()

    def write_profiles(self, profiles):
        lines = []
        for ssid, password in profiles.items():
            lines.append("{0};{1}\n".format(ssid, password))
        with open(self.sta_profiles, "w") as myfile:
            myfile.write("".join(lines))

    def read_profiles(self):
        try:
            with open(self.sta_profiles) as myfile:
                lines = myfile.readlines()
        except OSError:
            print("Could not open", self.sta_profiles)
            lines = []
            pass
        profiles = {}
        for line in lines:
            ssid, password = line.strip().split(";")
            profiles[ssid] = password
        return profiles

    def wifi_connect(self, ssid, password):
        print("Trying to connect to:", ssid)
        self.wlan_sta.connect(ssid, password)
        for _ in range(100):
            if self.wlan_sta.isconnected():
                print("\nConnected! Network information:", self.wlan_sta.ifconfig())
                return True
            else:
                print(".", end="")
                time.sleep_ms(100)
        print("\nConnection failed!")
        # Avoids a rescan block.
        self.wlan_sta.disconnect()
        return False

    # Here starts the web server part
    
    def web_server(self):
        # Let's start by activating the access point interface and then configuring it.
        print("Activating access point...")
        self.wlan_ap.active(True)
        self.wlan_ap.config(essid = self.ap_ssid, password = self.ap_password, authmode = self.ap_authmode)
        if self.ap_ip:
            self.wlan_ap.ifconfig((self.ap_ip, "255.255.255.0", self.ap_ip, self.ap_ip))
        # Close any open socket, just in case.
        server_socket = socket.socket()
        server_socket.close()
        # Open a new socket.
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("", 80))
        server_socket.listen(1)
        print("Connect to", self.ap_ssid, "with the password", self.ap_password, "and access the captive portal at", self.wlan_ap.ifconfig()[0])
        while True:
            if self.wlan_sta.isconnected():
                # Once we succeed to connect, we don't need the access point anymore.
                print("Deactivating access point...")
                self.wlan_ap.active(False)
                return True
            self.client, addr = server_socket.accept()
            print("Client connected from:", addr)
            try:
                self.client.settimeout(5.0)
                self.request = b""
                try:
                    while True:
                        if "\r\n\r\n" in self.request:
                            # Fix for Safari
                            self.request += self.client.recv(512)
                            break
                        self.request += self.client.recv(128)
                except OSError as e:
                    print(e)
                    pass
                # Avoid blank requests.
                if self.request:
                    print("REQUEST DATA:", self.request)
                    # Here we regex search for the specific url in the request string, and then proceed as needed.
                    url = ure.search("(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP", self.request).group(1).decode("utf-8").rstrip("/")
                    if url == "":
                        self.handle_root()
                    elif url == "configure":
                        self.handle_configure()
                    else:
                        self.handle_not_found()
            except Exception as e:
                print(e)
                return False
            finally:
                self.client.close()

    def send_header(self, status_code = 200):
        self.client.send("HTTP/1.1 {0} OK\r\n".format(status_code))
        self.client.send("Content-Type: text/html\r\n")
        self.client.send("Connection: close\r\n")

    def send_response(self, message, status_code = 200):
        self.send_header(status_code)
        self.client.sendall("""
            <!DOCTYPE html>
            <html lang="en">
                <head>
                    <title>{0}</title>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <link rel="icon" href="data:,">
                </head>
                <body>
                    <p>{1}</p>
                </body>
            </html>
        """.format(self.ap_ssid, message))
        self.client.close()

    def handle_root(self):
        self.send_header()
        self.client.sendall("""
            <!DOCTYPE html>
            <html lang="en">
                <head>
                    <title>{0}</title>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <link rel="icon" href="data:,">
                </head>
                <body>
                    <h1>WiFi Setup</h1>
                    <p>To connect to an open network, leave the password field blank.</p>
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

    def handle_configure(self):
        match = ure.search("ssid=([^&]*)&password=(.*)", self.request)
        if match:
            ssid = match.group(1).decode("utf-8").replace("%3F", "?").replace("%21", "!").replace("%23", "#")
            password = match.group(2).decode("utf-8").replace("%3F", "?").replace("%21", "!")
            if len(ssid) == 0:
                self.send_response("SSID must be providaded!", 400)
            elif self.wifi_connect(ssid, password):
                self.send_response("Successfully connected to {0}! IP address: {1}".format(ssid, self.wlan_sta.ifconfig()[0]))
                profiles = self.read_profiles()
                profiles[ssid] = password
                self.write_profiles(profiles)
                time.sleep(5)
            else:
                self.send_response("Could not connect to {0}! Go back and try again!".format(ssid))
                time.sleep(5)
        else:
            self.send_response("Parameters not found!", 400)
            time.sleep(5)

    def handle_not_found(self):
        self.send_response("Path not found!", 404)
        time.sleep(5)
