# Lotus T6e Live Tuner

## Disclaimer

***Use at your own risk. I have labelled these tables and addresses based on my interpretation of the ECU firmware. Modifying your ECU calibration can result in unexpected behaviour, including damage. I accept no liability for any damage caused as a result of using this application.***

## Introduction

This is a stripped back fork of Alcantors LotusECU-T4e tool. The monitoring and tuner applicaiton is now standalone.
This program is compatible with Lotus Exige V6 cars running the P138 firmware, with an unlocked calibration.

## Changes

1. Added datalogging. Clicking log will save all monitored variables to a CSV. Various free datalog viewer tools are available.

## Issues / Todo
 
- Closing tuner window results in a benign error. Will fix.
- Battery voltage address is wrong.
- Gear might work, haven't tested while moving.
- Need to add a safety check for forward/reverse scaling used when reading and writing to a table, otherwise user may inadvertently mismatch these when addding their own tables, causing written values to be wrong.
- Need to add colour to the gauge bars, user definable green/orange/red ranges.
- Need to add more tables to the live editor. 
