import time
import RPi.GPIO
import Adafruit_DHT
import requests
import json

from multiprocessing import Process


class TemperaturePoster:

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

        self.device_id = "10ab1023"  # This value will be taken from a file in later versions.

        self.poster = Process(target=self._post_temp)

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

        data = json.dumps({'temp': temp, 'device_id': self.device_id})
        response = requests.post(self.web_address, data)
        print(temp)  # This print statement won't be necessary once the post are working correctly.

    def _post_temp(self):
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

    def __del__(self):
        '''
        __del__ makes sure the self.poster process is terminated.

        :return: None
        '''

        self.stop_posting_temp()


tp = TemperaturePoster("http://www.tester.com")
tp.start_posting_temp()
time.sleep(5)
tp.stop_posting_temp()