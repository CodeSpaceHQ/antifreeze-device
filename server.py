from flask import Flask, send_from_directory, jsonify, request
from string import Template
import sh
import re


app = Flask(__name__)


@app.route("/")
def index():
    return send_from_directory("./public", "index.html")


@app.route("/wifi")
def getWifiNetworks():

    # Get the names of all the wifi networks available.
    answer = sh.grep(sh.iwlist("wlan0", "scan"),  "-Po", "(?<=ESSID:).*").stdout.decode("utf-8")

    # Put the wifi networks in answer into a list without duplication.
    answer = answer.strip()
    answer = re.split("\\s+", answer)
    answer = list(set(answer))

    return jsonify(answer)


@app.route("/submit", methods=["POST"])
def submit():

    # Get the data passed to the route.
    data = request.get_json()

    print("str :: " + str(data))
    print("POSTED")

    template = None

    # Read in the wpa_supplicant.conf_filled template file.
    with open("./config_files/wpa_supplicant.conf_filled", "r") as file:
        template = Template(file.read())

    # Put the values passed by the user into the wpa_supplicant template.
    wifi_signin = template.substitute(wifi_ssid=data["wifiNetwork"],
                                      wifi_password=data["wifiPassword"])

    with open("/etc/wpa_supplicant/wpa_supplicant.conf", "w") as file:
        file.write(wifi_signin)

    with open("./config_files/dhcpcd.conf_blank", "r") as file:
        dhcpcd_conf = file.read()

    with open("/etc/dhcpcd.conf", "w") as file:
        file.write(dhcpcd_conf)

    sh.systemctl("restart", "dhcpcd").stdout

    sh.systemctl("stop", "dnsmasq").stdout
    sh.systemctl("stop", "hostapd").stdout

    sh.wpa_cli( "-i", "wlan0", "reconfigure").stdout

    return send_from_directory("./public", "index.html")


class Server:

    def __init__(self, app):
        self.app = app

    def start(self):

        with open("./config_files/dhcpcd.conf_filled", "r") as file:
            dhcpcd_conf = file.read()

        with open("/etc/dhcpcd.conf", "w") as file:
            file.write(dhcpcd_conf)


        with open("./config_files/dnsmasq.conf", "r") as file:
            dhcpcd_conf = file.read()

        with open("/etc/dnsmasq.conf", "w") as file:
            file.write(dhcpcd_conf)


        with open("./config_files/hostapd.conf", "r") as file:
            dhcpcd_conf = file.read()

        with open("/etc/hostapd/hostapd.conf", "w") as file:
            file.write(dhcpcd_conf)

        sh.systemctl("start", "dnsmasq").stdout
        sh.systemctl("start", "hostapd").stdout

        self.app.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    server = Server(app)
    server.start()
