import Adafruit_DHT
import atexit
import json
import os
import pickle
import requests
import RPi.GPIO
import time


from multiprocessing import Process


class TemperaturePoster:
    '''
    TemperaturePoster post retrieves temperature data from the temperature sensor and posts it to the
    server.
    '''

    def __init__(self, web_address, update_interval=1):
        '''
        __init__ creates a TemperaturePoster object.

        :param self.web_address: <str> the web address to send the temperature data to.
        :param update_interval: <int> an integer grater than zero that is the number
            of seconds to wait before posting another temperature.
            Default Value: 1

        Class Variables:
        self.web_address: <str> the web address to send the temperature data to.
        self.update_interval: <int> an integer greater than zero that is the number
            of seconds to wait before posting another temperature.
        self.device_id: <str> a string that uniquely identifies this device to the server.
        self.poster: <Process> the process that continually gets and posts temperatures.
        '''

        # Make sure update_interval is in the range [1, inf).
        if update_interval < 1:
            update_interval = 1

        self.web_address = web_address

        self.update_interval = update_interval

        self.poster = Process(target=self.__post_temp)

        atexit.register(self.__exit)

    def get_temp(self):
        '''
        get_temp gets the temperature reading from the sensor.

        :return: <float> temperature in Celsius
        '''

        # Get the temperature and humidity from the temperature sensor.
        humidity, temp = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, 2)
        return temp

    def send_temp(self, temp):
        '''
        send_temp sends the temperature passed in to the server.

        :param temp: <float> the temperature to be sent to the server.
        :return: None
        '''

        data = json.dumps({'temp': temp, 'time': str(time.time())})
        response = requests.post(self.web_address, data)
        print(temp)  # This print statement won't be necessary once the post are working correctly.

    def __post_temp(self):
        '''
        _post_temp continually gets the temperature and then sends it to
        the server.

        :return: None
        '''

        while True:
            temp = self.get_temp()
            self.send_temp(temp)
            time.sleep(self.update_interval)

    def start_posting_temp(self):
        '''
        start_posting_temp starts getting the temperature and posting it to
        the server.

        :return: None
        '''

        # if self.poster is not already running:
        if not self.poster.is_alive():
            self.poster.start()

    def stop_posting_temp(self):
        '''
        stop_posting_temp stops getting the temperature and posting it to
        the server.

        :return: None
        '''

        # if self.poster is running:
        if self.poster.is_alive():
            self.poster.terminate()
            self.poster.join()

    def __exit(self):
        '''
        __exit makes sure the self.poster process is terminated.

        :return: None
        '''

        self.stop_posting_temp()


class Device:
    '''
    Device runs the RaspberryPi device.
    '''

    def __init__(self, web_address):

        self.web_address = web_address

        self.save_file_path = "./token.pkl"

        self.web_token = self.register_device(self.save_file_path)

        self.temp_poster = TemperaturePoster(web_address)

    def register_device(self, save_file_path):
        '''
        register_device loads the web token given to this device when it registered if the
        save file at save_file_path exists, otherwise it registers the device and creates the
        file at save_file_path.
        :param save_file_path: <str> the path to the save file if it exists or the path to where the
            save file will be created after the device is registered.
        :return: <str> the web token that was given to this device at registration
        '''

        # If the saved file exists:
        if os.path.isfile(save_file_path):
            # Get the data out of the file.
            with open(save_file_path, "rb") as file:
                saved_data = pickle.load(file)

            # Get the web token out of the data from the file.
            web_token = saved_data["web_token"]

        else:
            # Set the device to not registered.
            registered = False

            # While the device is not registered:
            while not registered:

                # Get information from the user.
                user_name = input("User Name :: ")
                password = input("Password :: ")
                device_name = input("Desired Device Name :: ")

                try:
                    # Assume that everything will work out and the device will successfully register.
                    registered = True

                    # Send the registration request to the server.
                    data = json.dumps({"userName": user_name, "password": password, "deviceName": device_name})
                    response = requests.post(self.web_address + "/register_device", data)

                except:
                    # Print an error message and correct the assumption that the device will successfully register.
                    print("Error Registering Device")
                    registered = False

            # Get the web token from the registration request.
            web_token = response["web_token"]

            # Save the web token into the file.
            with open(save_file_path, "wb+") as file:
                pickle.dumps({"web_token": web_token})

        return web_token

    def run(self):
        '''
        run runs the device.
        :return: None
        '''

        self.temp_poster.start_posting_temp()
        time.sleep(5)
        self.temp_poster.stop_posting_temp()


if __name__ == "__main__":
    device = Device("http://35.226.42.111:8081/device/")
    device.run()
