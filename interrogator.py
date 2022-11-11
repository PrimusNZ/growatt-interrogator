#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script for fetching data from Growatt inverter for MQTT
"""
from time import strftime
import time
import datetime
from configobj import ConfigObj
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from paho.mqtt import client as mqtt_client
import random
import requests
import sys
import json
from GrowattMap import GrowattMap

from apscheduler.schedulers.background import BackgroundScheduler

# read settings from config file
config = ConfigObj("/etc/growatt/pvinverter.cfg")
InverterPort = config['Inverter']
MqttBroker = config['MQTTBroker']
MqttPort = int(config['MQTTPort'])
MqttUser = config['MQTTUser']
MqttPass = config['MQTTPass']

# PVOutput Configurations
PVOEnabled = config['PVOEnabled']
SystemID = config['SystemID']
APIKey = config['APIKey']

Verbose = config['Verbose']

Mapfile = config['Mapfile']


# Static settings
MqttStub = "Growatt"
ReadRegisters = 101
client_id = f'inverter-stats-{random.randint(0, 1000)}'
gMap = GrowattMap(Mapfile)

try:
    Inverter = ModbusClient(method='rtu', port=InverterPort, baudrate=9600, stopbits=1, parity='N', bytesize=8, timeout=1)
    Inverter.connect()
    # Sanity Check to ensure registrs can be read
    Inverter.read_holding_registers(0,3)
    Inverter.read_input_registers(0,3)

except:
    print("")
    print("!!!!!!!!!!!!!!!!!!!!!!!!")
    print("!!! CONNECTION ERROR !!!")
    print("!!!!!!!!!!!!!!!!!!!!!!!!")
    print("Failed to connect to inverter on port: %s" %(InverterPort))
    print("")
    sys.exit()

def inverter_read():
  data={}
  #try:
    # Sending Current State
  holding_registers = Inverter.read_holding_registers(0,ReadRegisters)
  gMap.parse('holding', holding_registers.registers)

  input_registers = Inverter.read_input_registers(0,ReadRegisters)
  gMap.parse('input', input_registers.registers)

  data = gMap.finalise()
  #except:
  #  print("Exception while retrieving state")

  return data


def send_mqtt(client):
    data = inverter_read()
    for key, value in sorted(data.items()):
        publish(client, key, value)

def pv_upload():
    data = inverter_read()

    t_date = format(strftime('%Y%m%d'))
    t_time = format(strftime('%H:%M'))
    url="http://pvoutput.org/service/r2/addstatus.jsp"
    upload={'d':t_date,'t':t_time,'v2':data["pv_power"],'v4':data["consumption"],'v6':data["pv_volts"],'c1':"0"}
    api_headers={'X-Pvoutput-Apikey':APIKey,'X-Pvoutput-SystemId':SystemID}

    x = requests.post(url, data = upload, headers = api_headers)
    if Verbose.lower() == 'true':
        print("%s %s: Pushed data to PVOutput.org - %s" %(t_date, t_time, x.text))

def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
            # Discover to HA
            discovery_topics = gMap.discover()
            for payload in discovery_topics.items():
                if "__subscribe" in payload[1].keys():
                    del payload[1]["__subscribe"]
                    topic = ('%s/%s' %(MqttStub, payload[1]["command_topic"]))
                    client.subscribe(topic, qos=0)
                    print("Listening for cmnd changes on '%s'" %(topic))
                payload[1]["state_topic"]="%s/%s" %(MqttStub, payload[1]["state_topic"])
                client.publish(payload[0], json.dumps(payload[1], indent = 4),0,True)

        else:
            print("Failed to connect, return code %d\n", rc)
            quit()

    # Set Connecting Client ID
    client = mqtt_client.Client(client_id)
    client.username_pw_set(MqttUser, MqttPass)
    client.on_connect = on_connect
    #client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.connect(MqttBroker, MqttPort)
    return client


def on_message(client,userdata,message):
    topic = message.topic
    msg = message.payload.decode("utf-8")
    if Verbose.lower() == 'true':
        print("Received message: '%s' on '%s'" %(msg,topic))

    valid=False
    """
    try:

        if topic == ('%s/%s' %(MqttStub, MqttTopicPower)):
            if msg == "Battery First":
                set_register(1,0)
                publish(client, "state_power", msg)
            elif msg == "Solar First":
                set_register(1,1)
                publish(client, "state_power", msg)
            elif msg == "Grid First":
                set_register(1,2)
                publish(client, "state_power", msg)
            elif msg == "Solar and Grid First":
                set_register(1,3)
                publish(client, "state_power", msg)
        if topic == ('%s/%s' %(MqttStub, MqttTopicCharge)):
            if msg == "Solar First":
                set_register(2,0)
                publish(client, "state_charge", msg)
            elif msg == "Solar and Grid":
                set_register(2,1)
                publish(client, "state_charge", msg)
            elif msg == "Solar Only":
                set_register(2,2)
                publish(client, "state_charge", msg)
    except:
      print("Exception while changing state")
    """

def publish(client,stub,data):
    topic = ('%s/%s' %(MqttStub, stub))
    client.publish(topic, data)
    if Verbose.lower() == 'true':
        print("Published '%s' to '%s'" %(data, topic))

def run():
    print("Growatt Interrogator Starting")
    print("Verbose: %s" %(Verbose.lower()))
    print("Using serial port: %s" %(InverterPort))
    print("Publishing states to '%s/'" %(MqttStub))
    client = connect_mqtt()

    scheduler = BackgroundScheduler()
    scheduler.add_job(send_mqtt, 'interval', seconds=1, args=[client])
    if PVOEnabled.lower() == 'true':
        scheduler.add_job(pv_upload, 'cron', minute='*/5')
        print("Scheduled uploads to PVOutput every 5m are enabled")
    scheduler.start()

    client.loop_forever()

def set_register(register,value):
    success = False

    while success != True:
        try:
            # Read data from inverter
            holding_registers = Inverter.read_holding_registers(register,1)
            print ('%s -> %s' %(holding_registers.registers[0], value))
            Inverter.write_registers(register,value)

        except:
            print("Exception sending state change")
            time.sleep(1)
        else:
            success = True

if __name__ == '__main__':
    run()
