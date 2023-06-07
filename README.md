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
- [Home Assistant Supervised](https://github.com/home-assistant/supervised-installer) Recommended
- (Optionally) PVOutput account with System ID and API Key

## Installation

The installation of this add-on is pretty straightforward and not different in
comparison to installing any other Hass.io add-on.

1. [Add my Hass.io add-ons repository][repository] to your Hass.io instance.
1. Install this add-on.
1. Click the `Save` button to store your configuration.
1. Start the add-on.
1. Check the logs of the add-on to see if everything went well.
1. Carefully configure the add-on to your preferences, see the official documentation for for that.

[repository]: https://github.com/PrimusNZ/hassio-addons