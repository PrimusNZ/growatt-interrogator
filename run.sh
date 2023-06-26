#!/usr/bin/with-contenv bashio
set -e

cat > /etc/growatt/pvinverter.cfg <<EOF
# Register at pvoutput.org to get your SYSTEMID and APIKEY
PVOEnabled=$(bashio::config pvoutput_enabled)
SystemID=$(bashio::config pvoutput_systemid)
APIKey=$(bashio::config pvoutput_apikey)

# Inverter
Inverter=$(bashio::config inverter_port "/dev/ttyUSB0")
Mapfile=$(bashio::config mapfile)

# Logging
Verbose=$(bashio::config verbose)
Discovery=$(bashio::config discovery)

# MQTT For Inverter Interrorgator
MQTTBroker=$(bashio::services mqtt "host")
MQTTPort=1883
MQTTUser=$(bashio::services mqtt "username")
MQTTPass=$(bashio::services mqtt "password")

DebugRegisters=$(bashio::config debug_registers)
EOF

/interrogator.py
