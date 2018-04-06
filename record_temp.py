# import Adafruit_DHT
import atexit
import json
import logging
import os
import pickle
import requests
# import RPi.GPIO
import time


from multiprocessing import Process


class TemperaturePoster:
    '''
    TemperaturePoster post retrieves temperature data from the temperature sensor and posts it to the
    server.
    '''

    def __init__(self, web_address, web_token, update_interval=1):
        '''
        __init__ creates a TemperaturePoster object.

        :param self.web_address: <str> the web address to send the temperature data to.
        :param web_token: <str> the web token to post data to the server.
        :param update_interval: <int> an integer grater than zero that is the number
            of seconds to wait before posting another temperature.
            Default Value: 1

        Class Variables:
        self.web_address: <str> the web address to send the temperature data to.
        self.web_token: <str> the web token to post data to the server.
        self.update_interval: <int> an integer greater than zero that is the number
            of seconds to wait before posting another temperature.
        self.device_id: <str> a string that uniquely identifies this device to the server.
        self.poster: <Process> the process that continually gets and posts temperatures.
        '''

        # Make sure update_interval is in the range [1, inf).
        if update_interval < 1:
            update_interval = 1

        self.web_address = web_address

        self.web_token = web_token

        self.update_interval = update_interval

        self.poster = Process(target=self.__post_temp)

        atexit.register(self.__exit)

        logging.info("Temperature Poster Created :: self.web_address: %s, self.web_token not None: %r, "
                     "self.update_interval: %d", self.web_address, self.web_token is not None,
                     self.update_interval)

    def get_temp(self):
        '''
        get_temp gets the temperature reading from the sensor.

        :return: <float> temperature in Celsius
        '''

        # Get the temperature and humidity from the temperature sensor.
        #humidity, temp = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, 2)
        temp = 22.0
        return temp

    def send_temp(self, temp):
        '''
        send_temp sends the temperature passed in to the server.

        :param temp: <float> the temperature to be sent to the server.
        :return: None
        '''

        logging.info("Posting a temperature of %f degrees C.", temp)

        header = {"Authorization": "Bearer " + self.web_token}
        data = {"date": int(time.time()), "temp": temp}
        response = requests.post(self.web_address + "/rest/device/temp", headers=header, json=data)

    def __post_temp(self):
        '''
        __post_temp continually gets the temperature and then sends it to
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

        logging.info("Temperature Poster posting started.")

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

        logging.info("Temperature Poster posting stopped.")

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

    def __init__(self, web_address, token_save_file_path="./token.pkl"):
        '''
        __init__ creates a Device object.

        :param web_address: <str> the main web address that request will be made to
        :param token_save_file_path: <str> the path to where the token would be saved if the device was
            previously registered
            Default Value: "./token.pkl"

        Class Variables:
        self.web_address: <str> the main web address that request will be made to
        self.web_token: <str|None> the web token that was given on successful registration or
            None if registration was not successful
        self.temp_poster: <TemperaturePoster|None> a TemperaturePoster object that will be used to
            post temperatures to the server or None if the web token was not successfully gained
            (self.web_token is None)
        '''

        self.web_address = web_address

        self.web_token = self.get_web_token(token_save_file_path)

        self.temp_poster = None

        # If the web token was obtained successfully, then create the TemperaturePoster.
        if self.web_token is not None:
            self.temp_poster = TemperaturePoster(web_address, self.web_token)

        logging.info("Device Created :: self.web_address: %s, self.web_token is not None: %r",
                     self.web_address, self.web_token is not None)

    def register_device(self):
        '''
        register_device registers the device with the server.
        :return: <str|None> the web token returned upon successful registration
            or None if registration was not successful
        '''

        logging.info("Registering Device")

        # Set the web token to None as successful registration has not yet been achieved.
        web_token = None

        # Set the maximum number of attempts.
        max_num_attempts = 3

        # Set the number of registration attempts already tried.
        num_attempts = 0

        # While the device is not registered and the maximum number of attempts is not exceeded:
        while web_token is None and num_attempts < 3:

            # Get information from the user.
            email = input("User Email :: ")
            password = input("Password :: ")
            device_name = input("Desired Device Name :: ")

            # Send the registration request to the server.
            data = {"email": email, "password": password, "name": device_name}
            response = requests.post(self.web_address + "/rest/device/create", json=data)

            # If the request was successful:
            if response.status_code == 200:
                # Load the response data:
                response_data = json.loads(response.text)

                # Get the web token from the registration request.
                web_token = response_data["token"]

            # Else if the request failed with status code 400:
            elif response.status_code == 400:
                response_data = json.loads(response.text)
                print("ERROR :: " + response_data["message"])

            # Else the request failed with a status code other than 400.
            else:
                print("ERROR :: request failed with error code %d.", response.status_code)

            num_attempts += 1

        # If registration was not successful:
        if web_token is None:
            print("The maximum number of registration attempts has been exceeded.")
            logging.error("On device registration, maximum number of registration attempts exceeded.")

        return web_token

    def get_web_token(self, token_save_file_path):
        '''
        get_web_token gets the web token from the file specified by token_save_file_path if the file exists,
        otherwise it registers the device and saves the web token given.
        :param token_save_file_path: <str> the path to the save file if it exists or the path to where the
            save file will be created after the device is registered.
        :return: <str|None> the web token that was given to this device at registration or None if it
            could not register the device successfully.
        '''

        # If the saved file exists the device has already been registered:
        if os.path.isfile(token_save_file_path):
            # Get the data out of the file.
            with open(token_save_file_path, "rb") as file:
                saved_data = pickle.load(file)

            # Get the web token out of the data from the file.
            web_token = saved_data["web_token"]

        # The device has not yet been registered:
        else:
            # Attempt to register the device.
            web_token = self.register_device()

            # If the device was registered successfully:
            if web_token is not None:
                # Save the web token into the file.
                with open(token_save_file_path, "wb+") as file:
                    pickle.dump({"web_token": web_token}, file)

        return web_token

    def run(self):
        '''
        run runs the device.
        :return: None
        '''

        # If the TemperaturePoster self.temp_poster was created successfully:
        if self.temp_poster is not None:
            self.temp_poster.start_posting_temp()
            time.sleep(5)
            self.temp_poster.stop_posting_temp()


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',
                        filename='Debug.log', level=logging.DEBUG)
    device = Device("http://35.226.42.111:8081")
    device.run()
