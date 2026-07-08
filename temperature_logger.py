import time
import csv
import os
from datetime import datetime
import Adafruit_DHT #library to read temperature and humidity from DHT11 sensor

#name of CSV file to store temperature data
filename = "temperature_log.csv"

#prints the current working directory to help with debugging file path issues
print(os.getcwd())

#sensor type being used
sensor = Adafruit_DHT.DHT11
# Change this value if the sensor is connected to a different GPIO pin
pin = 4

#this function reads the temperature from the DHT11 sensor. It uses the Adafruit_DHT library to read the sensor data. The function returns the temperature value if it is successfully read; otherwise, it returns None.
def read_temp():
    humidity, temp = Adafruit_DHT.read(sensor, pin)
#humidity is not used in this code, but it can be logged if needed. The function returns the temperature value if it is successfully read; otherwise, it returns None.
    if temp is not None:
            # Check that the sensor successfully returned a temperature value
        save_data(timestamp, temp)
        return temp
    else:
        return None
        # Return None if the sensor reading fails


def create_file():
    with open(filename, "w") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "temperature"])

#Checks if the CSV file already exists.
def setup_file():
    if not os.path.exists(filename):
        create_file()


#Adds a new temperature reading to the CSV file.

def save_data(timestamp,temp):
    with open(filename, "a") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, tempe])


setup_file()

while True:
    temp = read_temp()
    timestamp = datetime.now()
    save_data(timestamp, temp)
    time.sleep(60)