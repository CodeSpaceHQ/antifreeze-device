from flask import Flask, send_from_directory, jsonify, request
from string import Template
import logging
import sh
import re


app = Flask(__name__)

running = False

info = None


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

    logging.info("Began submitting data.")

    # Get the data passed to the route.
    data = request.get_json()

    logging.info("Got data from the request sent.")

    global info
    info = {"username": data["username"],
            "password": data["password"],
            "deviceName": data["deviceName"],
            "webIP": data["webIP"]}

    logging.info("Global variable server.info set.")

    template = None

    # Read in the wpa_supplicant.conf_filled template file.
    with open("./config_files/wpa_supplicant.conf_filled", "r") as file:
        template = Template(file.read())

    # Put the values passed by the user into the wpa_supplicant template.
    wifi_signin = template.substitute(wifi_ssid=data["wifiNetwork"],
                                      wifi_password=data["wifiPassword"])

    with open("/etc/wpa_supplicant/wpa_supplicant.conf", "w") as file:
        file.write(wifi_signin)

    logging.info("Set the /etc/wpa_supplicant/wpa_supplicant.conf file with name: %s, password: %s"
                 % (data["wifiNetwork"], data["wifiPassword"]))

    with open("./config_files/dhcpcd.conf_blank", "r") as file:
        dhcpcd_conf = file.read()

    with open("/etc/dhcpcd.conf", "w") as file:
        file.write(dhcpcd_conf)

    logging.info("Set /etc/dhcpcd.conf with blank dhcpcd.conf file.")

    sh.systemctl("restart", "dhcpcd").stdout

    logging.info("Restarted dhcpcd with systemctl.")

    sh.systemctl("stop", "dnsmasq").stdout
    sh.systemctl("stop", "hostapd").stdout

    logging.info("Stopped dnsmasq and hostapd with systemctl.")

    sh.wpa_cli( "-i", "wlan0", "reconfigure").stdout

    logging.info("Turned on wifi with wpa_cli -i wlan0 reconfigure")

    stop()

    return send_from_directory("./public", "index.html")


def stop():

    logging.info("Began stopping server.")

    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

    logging.info("Server stopped.")

    global running
    running = False

    logging.info("Set server.running gloabl variable to False.")


def start():

    logging.info("Began starting the server.")

    with open("./config_files/dhcpcd.conf_filled", "r") as file:
        dhcpcd_conf = file.read()

    with open("/etc/dhcpcd.conf", "w") as file:
        file.write(dhcpcd_conf)

    logging.info("Replaced the /etc/dhcpcd.conf file.")


    with open("./config_files/dnsmasq.conf", "r") as file:
        dhcpcd_conf = file.read()

    with open("/etc/dnsmasq.conf", "w") as file:
        file.write(dhcpcd_conf)

    logging.info("Replaced the /etc/dnsmasq.conf file.")


    with open("./config_files/hostapd.conf", "r") as file:
        dhcpcd_conf = file.read()

    with open("/etc/hostapd/hostapd.conf", "w") as file:
        file.write(dhcpcd_conf)

    logging.info("Replaced the /etc/hostapd/hostapd.conf file.")

    sh.systemctl("restart", "dhcpcd").stdout

    logging.info("Restarted dhcpcd with systemctl.")

    sh.systemctl("start", "dnsmasq").stdout
    sh.systemctl("start", "hostapd").stdout

    logging.info("Started dnsmasq and hostapd with systemctl.")

    global running
    running= True

    logging.info("Set server.running gloabl variable to True.")

    app.run(host="0.0.0.0", port=5000)

    logging.info("Started the app running on 0.0.0.0:5000.")


if __name__ == "__main__":
    start()
