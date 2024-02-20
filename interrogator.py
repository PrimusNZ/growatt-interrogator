#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Script for fetching data from Growatt inverter for MQTT
"""
from time import strftime
import time
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from paho.mqtt import client as mqtt_client
from os import environ as env
import random
import requests
import sys
import json
from GrowattMap import GrowattMap

from apscheduler.schedulers.background import BackgroundScheduler

# read settings from config file
InverterPort = env.get('INVERTER_PORT')
MqttBroker = env.get('MQTT_HOST')
MqttPort = int(env.get('MQTT_PORT'))
MqttUser = env.get('MQTT_USER')
MqttPass = env.get('MQTT_PASSWORD')

# Sync Time on Start-up?
TimeSync = env.get('TIME_SYNC')

# PVOutput Configurations
PVOEnabled = env.get('PVO_ENABLED')
SystemID = env.get('PVO_SYSTEMID')
APIKey = env.get('PVO_APIKEY')

DebugRegisters = env.get('DEBUG_REGISTERS').split(",")

if env.get('VERBOSE').lower() == 'true':
    Verbose = True
else:
    Verbose = False

if env.get('DISCOVERY').lower() == 'false':
    Discovery = False
else:
    Discovery = True

Mapfile = env.get('MAPFILE')


# Static settings
MqttStub = "gwi"
ReadRegisters = 101
client_id = f'inverter-stats-{random.randint(0, 1000)}'
gMap = GrowattMap(Mapfile, DebugRegisters)

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
  try:
    # Sending Current State
    registers = []
    register_ranges = gMap.get_register_ranges("holding")
    
    for range in register_ranges:
        holding_registers = Inverter.read_holding_registers(range[0],range[1], unit=0x1)
        registers.extend(holding_registers.registers)
    gMap.parse('holding', registers)

    registers = []
    register_ranges = gMap.get_register_ranges("input")
    for range in register_ranges:
        input_registers = Inverter.read_input_registers(range[0],range[1], unit=0x1)
        registers.extend(input_registers.registers)
    gMap.parse('input', registers)

    data = gMap.finalise()
  except Exception as e:
    print("Exception while retrieving state: %s" %(e))

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
    upload={'d':t_date,'t':t_time,'v2':data["pv_power"],'v4':data["output_power"],'v6':data["pv_volts"],'c1':"0"}
    api_headers={'X-Pvoutput-Apikey':APIKey,'X-Pvoutput-SystemId':SystemID}

    x = requests.post(url, data = upload, headers = api_headers)
    if Verbose:
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
                    payload[1]["command_topic"]=topic
                    print("Listening for cmnd changes on '%s'" %(topic))
                payload[1]["state_topic"]="%s/%s" %(MqttStub, payload[1]["state_topic"])
                if Discovery:
                    client.publish(payload[0], json.dumps(payload[1], indent = 4),0,True)
                else:
                    client.publish(payload[0], "",0,True)

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
    if Verbose:
        print("Received message: '%s' on '%s'" %(msg,topic))

    valid=False

    try:
        topic_stub = topic.replace("%s/cmnd/" %(MqttStub),"")
        register = gMap.decode_mqtt(topic_stub, msg)
        if register != False:
            set_register(register[0],register[1])
            publish(client, topic_stub, msg)
    except Exception as e:
      print("Exception while changing state: %s" %(e))

def publish(client,stub,data):
    topic = ('%s/%s' %(MqttStub, stub))
    client.publish(topic, data)
    if Verbose:
        print("Published '%s' to '%s'" %(data, topic))

def run():
    print("Growatt Interrogator Starting")
    print("Verbose: %s" %(Verbose))
    print("Using serial port: %s" %(InverterPort))
    print("Publishing states to '%s/'" %(MqttStub))
    if TimeSync.lower() == 'true':
        print("Syncing Inverter time to system time")
        set_register(45, int(strftime("%Y")))
        set_register(46, int(strftime("%m")))
        set_register(47, int(strftime("%d")))
        set_register(48, int(strftime("%H")))
        set_register(49, int(strftime("%M")))
        set_register(50, int(strftime("%S")))

    print("Connecting to MQTT")
    client = connect_mqtt()

    print("Starting Background Scheduler")
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
            if Verbose:
                print ('Register %s changed from %s to %s' %(register, holding_registers.registers[0], value))
            Inverter.write_registers(register,value)

        except Exception as e:
            print("Exception sending state change: %s" %(e))
            time.sleep(1)
        else:
            success = True

if __name__ == '__main__':
    run()
