# Growatt Interrogator

## About
A simple (very poorly written) Python 3 script to interrogate a Growatt Inverter for power information via USB and publishes to Home Assistant via MQTT.
Optionally uploads data to [PVOutput.org](https://pvoutput.org) for tracking solar generation and overall consumption

Example: [Bus'Ted Solar Generation](https://pvoutput.org/list.jsp?sid=88110)

## MQTT ##
Once up and running, this addon will automatically send all sensors to Home Assistant

### Auto Discovery ###
Home Assistant should pick up all the Growatt sensors automatically via the MQTT auto discovery method - This currently cannot be disabled - Coming Soon.

### MQTT Topics  ###
The Growatt Interrogator addon publishes to the gwi/ prefix.

## MAY NOT WORK WITH HASSOS
HassOS MAY possibly lack certain kernel modules required to correctly communicate with your inverter.
It is recommended to run this addon on top of [Home Assistant Supervised](https://github.com/home-assistant/supervised-installer)

Inverters using the usbserial kernel driver should work. Your milage may vary.

## Requirements

- Growatt Invertor plugged into your Home Assistant instance via USB
- MQTT Server
- (Optionally) PVOutput account with System ID and API Key

## Installation
```
version: '3'

services:
  growatt-interrogator:
    image: "ghcr.io/primusnz/growatt-interrogator:master"
    container_name: growatt-interrogator
    restart: unless-stopped
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0 # Your Inverter 
    environment:
      - MAPFILE=default
      - INVERTER_PORT=/dev/ttyUSB0
      - MQTT_HOST=192.168.X.X
      - MQTT_PORT=1883
      - MQTT_USER=USERNAME
      - MQTT_PASSWORD=PASSWORD
      - PVO_ENABLED=false
      - PVO_SYSTEMID=
      - PVO_APIKEY=
      - DEBUG_REGISTERS=
      - VERBOSE=false
      - DISCOVERY=true
      - TIME_SYNC=True
```