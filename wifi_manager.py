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

    def __init__(self, ssid = "WifiManager", password = "wifimanager", ip = "1.2.3.4", timeout = None):
        self.wlan_sta = network.WLAN(network.STA_IF)
        self.wlan_sta.active(True)
        self.wlan_ap = network.WLAN(network.AP_IF)
        self.ap_ssid = ssid
        self.ap_password = password
        self.ap_ip = ip
        self.ap_timeout = timeout
        self.ap_authmode = 3
        self.sta_profiles = "wifi.dat"
        self.wlan_sta.disconnect()

    def check_connection(self):
        # If it's already connected, why to connect again?
        if self.wlan_sta.isconnected():
            return True
        else:
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
            # And if it fail to connect we start the captive portal.
            print("Could not connect to any WiFi network. Starting the captive portal...")
            if self.start_server():
                return True
            else:
                return False

    def write_profiles(self, profiles):
        lines = []
        for ssid, password in profiles.items():
            lines.append("%s;%s\n" % (ssid, password))
        with open(self.sta_profiles, "w") as myfile:
            myfile.write("".join(lines))

    def read_profiles(self):
        try:
            with open(self.sta_profiles) as myfile:
                lines = myfile.readlines()
        except OSError as e:
            print("Could not open", self.sta_profiles, "file.", e)
            lines = []
            pass
        profiles = {}
        for line in lines:
            ssid, password = line.strip("\n").split(";")
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
    
    def start_server(self):
        # Let's start by activating the access point interface and then configuring it.
        print("Activating access point...")
        self.wlan_ap.active(True)
        self.wlan_ap.config(essid = self.ap_ssid, password = self.ap_password, authmode = self.ap_authmode)
        self.wlan_ap.ifconfig((self.ap_ip, "255.255.255.0", self.ap_ip, self.ap_ip))
        # Close any open socket, just in case.
        server_socket = socket.socket()
        server_socket.close()
        # Open a new socket.
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("", 80))
        server_socket.listen(1)
        print("Connect to", self.ap_ssid, "with the password", self.ap_password, "and access the captive portal at", self.ap_ip)
        while True:
            if self.wlan_sta.isconnected():
                # Once we succeed to connect, we don't need the access point anymore.
                print("Deactivating access point...")
                self.wlan_ap.active(False)
                return True
            else:
                self.client, addr = server_socket.accept()
                print("Client connected from:", addr)
                try:
                    self.client.settimeout(self.ap_timeout)
                    self.request = b""
                    try:
                        while "\r\n\r\n" not in self.request:
                            self.request += self.client.recv(128)
                    except OSError as e:
                        print("Request timed out...", e)
                        return False
                    # After that we regex search for the specific url in the request string, and then proceed as needed.
                    url = ure.search("(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP", self.request).group(1).decode("utf-8").rstrip("/")
                    if url == "":
                        self.handle_root()
                    elif url == "configure":
                        self.handle_configure()
                    else:
                        self.handle_not_found()
                except OSError as e:
                    print(e)
                    return False
                finally:
                    self.client.close()

    def send_header(self, status_code = 200):
        self.client.send("HTTP/1.1 {0} OK\r\n".format(status_code))
        self.client.send("Content-Type: text/html\r\n")

    def send_response(self, message, status_code = 200):
        self.send_header(status_code)
        self.client.sendall("""
            <!DOCTYPE html>
            <html lang="en">
                <head>
                    <title>{0}</title>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
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
                </head>
                <body>
                    <h1>WiFi Setup</h1>
                    <form action="configure" method="post">
        """.format(self.ap_ssid))
        for ssid, *_ in self.wlan_sta.scan():
            ssid = ssid.decode("utf-8")
            self.client.sendall("""
                        <p><input type="radio" name="ssid" id="{0}" value="{0}"><label for="{0}">&nbsp;{0}</label></p>
            """.format(ssid))
        self.client.sendall("""
                        <p><label for="password">Password:&nbsp;</label><input type="password" id="password" name="password"></p>
                        <p><input type="submit" value="Connect!"></p>
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
