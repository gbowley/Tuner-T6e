# Lotus T6e Live Tuner

## Disclaimer

***Use at your own risk. I have labelled these tables and addresses based on my interpretation of the ECU firmware. Modifying your ECU calibration can result in unexpected behaviour, including damage. I accept no liability for any damage caused as a result of using this application.***

## Introduction

This is a stripped back fork of Alcantors LotusECU-T4e tool. The monitoring and live tuner applicaiton is now standalone.
This program is compatible with Lotus Exige V6 cars running the P138 firmware, with an unlocked calibration.

For firmware flashing use [LotusECU-T4e](https://github.com/Alcantor/LotusECU-T4e)

## Installation (usb2can)

1.  **Python:** Ensure you have Python 3 installed. The recommended install is [3.9.7](https://www.python.org/downloads/release/python-397/) for environment compatibility with [Lotus Flasher](https://github.com/Alcantor/LotusECU-T4e)
2.  **Dependencies:** Install the required Python libraries. The primary dependencies are `python-can`, and `pyserial`. Open an elevated command prompt and run the following.
    ```bash
    pip install python-can
    pip install pyserial
    # Add any other specific dependencies if identified, e.g., for a specific CAN interface backend
    # pip install can-isotp # (Potentially needed depending on python-can version and usage)
    ```
3.  **CAN Interface Driver 1:** Install the necessary drivers for the [Korlan](https://shop.8devices.com/index.php?route=product/product&path=67&product_id=89) Adapter, including the [Windows Driver](https://drive.google.com/drive/folders/1gXWpuP20U2mhcW6IqtwhRo0PY9ZusSYv)
4. **CAN Interface Driver 2:** Install the [USB2CAN](https://drive.google.com/file/d/1_xSpR1bGE3OQN6w0EG9WmrvtgatyQa05/view) driver by placing `usb2can.dll` in your Python install directory.

## Usage

Launch Tuner.py

## Changes

1. Added datalogging. Clicking log will save all monitored variables to a CSV. Various free datalog viewer tools are available.

## Issues / Todo
 
- Closing tuner window results in a benign error. Will fix.
- Battery voltage address is wrong.
- Gear might work, haven't tested while moving.
- Need to add a safety check for forward/reverse scaling used when reading and writing to a table, otherwise user may inadvertently mismatch these when addding their own tables, causing written values to be wrong.
- Need to add colour to the gauge bars, user definable green/orange/red ranges.
- Need to add more tables to the live editor. 
