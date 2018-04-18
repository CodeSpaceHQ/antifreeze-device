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

    # Read in the wpa_supplicant.conf template file.
    with open("./config_files/wpa_supplicant.conf", "r") as file:
        template = Template(file.read())

    # Put the values passed by the user into the wpa_supplicant template.
    wifi_signin = template.substitute(wifi_ssid=data["wifinetwork"],
                                      wifi_password='"' + data["wifipassword"] + '"')

    with open("/etc/wpa_supplicant/wpa_supplicant.conf", "a") as file:
        file.write(wifi_signin)

    sh.systemctl("stop", "dnsmasq").stdout
    sh.systemctl("stop", "hostapd").stdout

    sh.wpa_cli( "-i", "wlan0", "reconfigure").stdout

    return send_from_directory("./public", "index.html")


class Server:

    def __init__(self, app):
        self.app = app

    def start(self):
        self.app.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    server = Server(app)
    server.start()
