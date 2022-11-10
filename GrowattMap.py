import yaml

class GrowattMap:

    def __init__(self,mapFile):
        self.return_keys = {}
        mapPath = "/etc/growatt/maps/%s.yaml" %(mapFile)
        print(mapPath)
        with open(mapPath, 'r') as f:
            self.growattMap = yaml.load(f, Loader=yaml.FullLoader)

    def parse(self, register_map, registers):
        self.registers = registers
        if (register_map in self.growattMap["registers"]):
            for key in self.growattMap["registers"][register_map].keys():
                if key in registers:
                    result = self.__calculate_key(key, self.growattMap["registers"][register_map][key])
                    self.return_keys = {**self.return_keys, **result}

    def finalise(self):
        if "transform" in self.growattMap.keys():
            transforms = self.growattMap["transform"]
            for key in transforms:
                result =self.__calculate_transform_key(key, transforms[key])
                self.return_keys = {**self.return_keys, **result}

        return self.return_keys

    def __calculate_key(self, key, definition):
        key_name = self.__convert_name(definition["name"])
        def_keys = definition.keys()
        value = self.__fetch_raw(key)

        if "add" in def_keys:
            add = self.__fetch_raw(definition["add"])
            value=value+add
        elif "subtract" in def_keys:
            subtract = self.__fetch_raw(definition["add"])
            value=value-subtract

        if "type" in def_keys:
            key_type = definition["type"]
            if key_type=="int":
                value=int(value)
            elif key_type=="float":
                value=float(value)
        else:
            value=int(value)

        if "states" in def_keys:
            states = definition["states"]
            if value in states:
                value = states[value]
            else:
                value = "ERROR"
        elif "math" in def_keys:
            math=definition["math"].replace("a","%s" %(value))
            value=eval(math)

        if "round" in def_keys:
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
                value="true"
            else:
                value="false"

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

        if "round" in def_keys:
            value=round(value,int(transform["round"]))

        return {key_name: value}

    def __convert_name(self, name):
        return name.lower().replace(" ","_")

    def __fetch_raw(self, key):
        return self.registers[key]
