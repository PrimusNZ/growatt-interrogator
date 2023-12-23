import yaml
import ctypes
import struct
import math
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian

class GrowattMap:

    def __init__(self,map_file,debug_registers):
        self.return_keys = {}
        mapPath = "/etc/growatt/maps/%s.yaml" %(map_file)
        with open(mapPath, 'r') as f:
            self.growattMap = yaml.load(f, Loader=yaml.FullLoader)
        self.debug_registers = debug_registers

    def parse(self, register_map, registers):
        self.registers = registers
        if (register_map in self.growattMap["registers"]):
            for key in self.growattMap["registers"][register_map].keys():
                result = self.__calculate_key(key, self.growattMap["registers"][register_map][key])
                self.return_keys = {**self.return_keys, **result}

    def finalise(self):
        if "transform" in self.growattMap.keys():
            transforms = self.growattMap["transform"]
            for key in transforms:
                result =self.__calculate_transform_key(key, transforms[key])
                self.return_keys = {**self.return_keys, **result}

        return self.return_keys

    def get_register_ranges(self, register_map):
        if (register_map in self.growattMap["registers"]):
            max_key=0
            register_maps=[]
            for key in self.growattMap["registers"][register_map].keys():
                if key > max_key:
                    max_key = key
            starting_reg=0
            last_reg=0
            loops = math.ceil(max_key/100)
            for x in range(loops):
                register_maps.append([last_reg,100])
                last_reg = last_reg+100
            return register_maps
        else:
            return [0]


    def __calculate_key(self, key, definition):
        key_name = self.__convert_name(definition["name"])
        def_keys = definition.keys()
        value = self.__fetch_raw(key)
        if str(key) in self.debug_registers:
            Debug=True
        else:
            Debug=False
        
        if "double" in def_keys:
            v1 = value
            v2 = self.__fetch_raw(definition["double"])
            value = float((v1 << 16) + v2)
            if Debug:
                print("Double: (%s<<16)+%s = %s" %(v1, v2, value))
            #decoder = BinaryPayloadDecoder.fromRegisters([v1,v2], byteorder=Endian.Big, wordorder=Endian.Big)
            #value=decoder.decode_32bit_int()

        if "add" in def_keys:
            add = self.__fetch_raw(definition["add"])
            if Debug:
                print("Add: %s+%s" %(value, add))
            value=value+add
        elif "subtract" in def_keys:
            subtract = self.__fetch_raw(definition["subtract"])
            if Debug:
                print("Subtract: %s+%s" %(value, subtract))
            value=value-subtract

        if "states" in def_keys:
            states = definition["states"]
            if Debug:
                print("States: %s in %s" %(value, states))
            if value in states:
                value = states[value]
            else:
                value = "ERROR"
        elif "math" in def_keys:
            math=definition["math"].replace("a","%s" %(value))
            if Debug:
                print("Math: %s" %(math))
            value=eval(math)

        if "data_type" in def_keys:
            key_type = definition["data_type"]
            if Debug:
                print("Data Type: %s" %(key_type))
            if key_type=="int":
                value=int(value)
            elif key_type=="float":
                value=float("{:.2f}".format(float(value)))
        else:
            value=str(value)

        if "round" in def_keys:
            if Debug:
                print("Round: %s" %(value))
            value=round(value,int(definition["round"]))

        return {key_name: value}

    def __calculate_transform_key(self, key, transform):
        key_name = self.__convert_name(key)
        def_keys = transform.keys()
        values=[]
        replacements=["a","b","c","d"]

        if "sources" in def_keys:
            for source in transform["sources"]:
                source = self.__convert_name(source)
                if source in self.return_keys:
                    value = self.return_keys[source]
                    values.append(value)
        else:
            return {}

        if "condition" in def_keys:
            condition=transform["condition"].replace("a","%s" %(values[0]))
            if eval(condition):
                value="ON"
            else:
                value="OFF"

        if "math" in def_keys:
            replacements = len(values)
            math=transform["math"]
            if replacements>=1:
                math=math.replace("a","%s" %(values[0]))
            if replacements>=2:
                math=math.replace("b","%s" %(values[1]))
            if replacements>=3:
                math=math.replace("c","%s" %(values[2]))
            if replacements==4:
                math=math.replace("d","%s" %(values[3]))
            value=eval(math)

        if "data_type" in def_keys:
            key_type = transform["data_type"]
            if key_type=="int":
                value=int(value)
            elif key_type=="float":
                value=float("{:.2f}".format(float(value)))
        else:
            value=str(value)

        if "round" in def_keys:
            value=round(value,int(transform["round"]))

        return {key_name: value}

    def __convert_name(self, name):
        return name.lower().replace(" ","_")

    def __fetch_raw(self, key):
        return self.registers[key]

    def __construct_payload(self, definition):
        topic = "homeassistant/%s/gwi_%s/config" %(definition["type"], self.__convert_name(definition["name"]))
        payload={
            "name": "Growatt %s" %(definition["name"]),
            "unique_id": "gwi_%s" %(self.__convert_name(definition["name"])),
            "state_topic": self.__convert_name(definition["name"])
        }

        if "device_class" in definition:
            payload["device_class"] = definition["device_class"]

        if "unit_of_measurement" in definition:
            payload["unit_of_measurement"] = definition["unit_of_measurement"]

        if "payload_on" in definition:
            payload["payload_on"] = definition["payload_on"]
        if "payload_off" in definition:
            payload["payload_off"] = definition["payload_off"]

        if "state_class" in definition:
            payload["state_class"] = definition["state_class"]

        if "icon" in definition:
            payload["icon"] = definition["icon"]

        if definition["type"]=="select":
            states=[]
            for state in definition["states"].items():
                states.append(state[1])
            payload["options"] = states
            payload["command_topic"]="cmnd/%s" %(self.__convert_name(definition["name"]))
            payload["__subscribe"]=True

        return {topic:payload}

    def discover(self):
        payloads={}
        if "input" in self.growattMap["registers"]:
            for key in self.growattMap["registers"]["holding"]:
                definition = self.growattMap["registers"]["holding"][key]
                payload = self.__construct_payload(definition)
                payloads = {**payloads, **payload}

        if "holding" in self.growattMap["registers"]:
            for key in self.growattMap["registers"]["input"]:
                definition = self.growattMap["registers"]["input"][key]
                payload = self.__construct_payload(definition)
                payloads = {**payloads, **payload}

        if "transform" in self.growattMap.keys():
            for key in self.growattMap["transform"]:
                definition = self.growattMap["transform"][key]
                definition["name"] = key
                payload = self.__construct_payload(definition)
                #definition = self.growattMap["transform"][key]
                #print(definition)
                payloads = {**payloads, **payload}

        return payloads

    def decode_mqtt(self, topic, cmnd):
        name = topic.replace("_", " ")
        for register in self.growattMap["registers"]['holding'].keys():
            key = self.growattMap["registers"]['holding'][register]
            if name == key['name'].lower():
                states = key["states"]
                for value in states:
                    if cmnd.lower() == states[value].lower():
                        return [register,value]
        return False