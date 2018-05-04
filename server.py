from flask import Flask, send_from_directory, jsonify, request
from string import Template
import logging
import sh
import re


# app is the actual Flask server.
app = Flask(__name__)

# running is True when app is running and False otherwise.
running = False

# info is a dictionary that contains all the input the user supplied, and None
# if the user has not yet supplied any input.
info = None


@app.route("/")
def index():
    '''
    index is the initial method that returns the website's main page.
    :return: <html> the html page to be rendered by the client.
    '''

    return send_from_directory("./public", "index.html")


@app.route("/wifi")
def getWifiNetworks():
    '''
    getWifiNetworks gets the wifi networks that the raspberry pi can see.
    :return: <str> a json object containing all the wifi networks available.
    '''

    # Get the names of all the wifi networks available.
    answer = sh.grep(sh.iwlist("wlan0", "scan"),  "-Po", "(?<=ESSID:).*").stdout.decode("utf-8")

    # Put the wifi networks in answer into a list without duplication.
    answer = answer.strip()
    answer = re.split("\\s+", answer)
    answer = list(set(answer))

    return jsonify(answer)


@app.route("/submit", methods=["POST"])
def submit():
    '''
    submit is called when the user submits the data the put on the web page.
    :return: <html> the main page
    '''

    logging.info("Began submitting data.")

    # Get the data passed to the route.
    data = request.get_json()

    logging.info("Got data from the request sent.")

    # Put the user's input into the global info vaiable.
    global info
    info = {"username": data["username"],
            "password": data["password"],
            "deviceName": data["deviceName"],
            "webIP": data["webIP"]}

    logging.info("Global variable server.info set.")

    template = None

    # Read in the wpa_supplicant.conf_filled template file.
    with open("/home/pi/Desktop/antifreeze-device/config_files/wpa_supplicant.conf_filled", "r") as file:
        template = Template(file.read())

    # Put the values passed by the user into the wpa_supplicant template.
    wifi_signin = template.substitute(wifi_ssid=data["wifiNetwork"],
                                      wifi_password=data["wifiPassword"])

    # Replace the wpa_supplicant.conf with the new one that was constructed from the template.
    with open("/etc/wpa_supplicant/wpa_supplicant.conf", "w") as file:
        file.write(wifi_signin)

    logging.info("Set the /etc/wpa_supplicant/wpa_supplicant.conf file with name: %s, password: %s"
                 % (data["wifiNetwork"], data["wifiPassword"]))

    # Get the blank dhcpcd.conf file.
    with open("/home/pi/Desktop/antifreeze-device/config_files/dhcpcd.conf_blank", "r") as file:
        dhcpcd_conf = file.read()

    # Replace the filled dhcpcd.conf file with the blank one that was just read in.
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

    # Turn the server off.
    stop()

    return send_from_directory("./public", "index.html")


def stop():
    '''
    stop turns off the Flask server.
    :return: None
    '''

    logging.info("Began stopping server.")

    # Turn off the server.
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

    logging.info("Server stopped.")

    # Set the global variable running to False because the server is no longer
    # running.
    global running
    running = False

    logging.info("Set server.running gloabl variable to False.")


def start():
    '''
    start starts the server.
    :return: None
    '''

    logging.info("Began starting the server.")

    # Open the filled dhcpcd.conf file and read it in.
    with open("/home/pi/Desktop/antifreeze-device/config_files/dhcpcd.conf_filled", "r") as file:
        dhcpcd_conf = file.read()

    # Replace the current dhcpcd.conf file with the one that was just read in.
    with open("/etc/dhcpcd.conf", "w") as file:
        file.write(dhcpcd_conf)

    logging.info("Replaced the /etc/dhcpcd.conf file.")

    # Open the dnsmasq.conf file and read it in.
    with open("/home/pi/Desktop/antifreeze-device/config_files/dnsmasq.conf", "r") as file:
        dhcpcd_conf = file.read()

    # Replace the current dnsmasq.conf file with the one that was just read in.
    with open("/etc/dnsmasq.conf", "w") as file:
        file.write(dhcpcd_conf)

    logging.info("Replaced the /etc/dnsmasq.conf file.")

    # Open the dnsmasq.conf file and read it in.
    with open("/home/pi/Desktop/antifreeze-device/config_files/hostapd.conf", "r") as file:
        dhcpcd_conf = file.read()

    # Replace the current hostapd.conf file with the one that was just read in.
    with open("/etc/hostapd/hostapd.conf", "w") as file:
        file.write(dhcpcd_conf)

    logging.info("Replaced the /etc/hostapd/hostapd.conf file.")

    sh.systemctl("restart", "dhcpcd").stdout

    logging.info("Restarted dhcpcd with systemctl.")

    sh.systemctl("start", "dnsmasq").stdout
    sh.systemctl("start", "hostapd").stdout

    logging.info("Started dnsmasq and hostapd with systemctl.")

    # Set the global varable running to True because the server is now running.
    global running
    running= True

    logging.info("Set server.running gloabl variable to True.")

    # Turn on the server at localhost:5000.
    app.run(host="0.0.0.0", port=5000)

    logging.info("Started the app running on 0.0.0.0:5000.")


if __name__ == "__main__":
    start()
