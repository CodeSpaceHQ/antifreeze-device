from flask import Flask, send_from_directory, jsonify, request
import sh
import re


app = Flask(__name__)


@app.route("/")
def index():
    return send_from_directory("./public", "index.html")


@app.route("/wifi")
def getWifiNetworks():
    answer = sh.ls(".").stdout.decode("utf-8")

    answer = answer.strip()

    answer = re.split("\\s+", answer)

    print(answer)

    return jsonify(answer)


@app.route("/submit", methods=["POST"])
def submit():

    data = request.get_json()

    print("str :: " + str(data))
    print("POSTED")

    return "DONE"

class Server:

    def __init__(self, app):
        self.app = app

    def start(self):
        self.app.run()


if __name__ == "__main__":
    server = Server(app)
    server.start()
