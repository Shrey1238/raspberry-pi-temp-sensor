# Raspberry Pi Temperature Logger

A Python-based temperature logging system using a Raspberry Pi and a DHT11 temperature sensor. The program collects temperature readings at regular intervals, records the time of each measurement, and stores the data in a CSV file for later analysis.

## Features

* Reads temperature data from a DHT11 sensor
* Records the date and time of each measurement
* Stores readings in a CSV file
* Automatically creates the CSV file if it does not already exist
* Preserves previous measurements by appending new data
* Runs continuously at a user-defined interval

## Hardware Requirements

* Raspberry Pi
* DHT11 Temperature Sensor Module
* Jumper wires
* MicroSD card with Raspberry Pi OS installed

## Software Requirements

* Python 3
* Adafruit DHT Python library

Install the required library with:

```bash
pip3 install Adafruit-DHT
```

## Wiring

Example wiring:

| DHT11 Pin | Raspberry Pi |
| --------- | ------------ |
| VCC       | 3.3V         |
| DATA      | GPIO 4       |
| GND       | Ground       |

If a different GPIO pin is used, update the pin number in the Python program.

## How It Works

The program follows this process:

1. Check whether the CSV file exists
2. Create the file and add headers if needed
3. Read temperature data from the DHT11 sensor
4. Record the current timestamp
5. Save the temperature and timestamp to the CSV file
6. Wait for the selected interval
7. Repeat the process

## File Structure

```
RaspberryPiProjects/
│
├── temperature_logger.py
├── temperature_log.csv
└── README.md
```

## CSV Output Example

The generated CSV file will look like:

```csv
timestamp,temperature
2026-07-08 15:30:00,23
2026-07-08 15:31:00,23
2026-07-08 15:32:00,24
```

## Future Improvements

Possible additions:

* Add humidity logging
* Create temperature graphs
* Add cloud data storage
* Add error handling for sensor failures
* Create a web dashboard for live monitoring

## Author

Shrey1238
