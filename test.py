#!/usr/bin/env python3
# coding: utf-8

import io
import sys
import re
import json
import subprocess
import pandas as pd
from subprocess import PIPE


class PowerVaultMD():
    def __init__(self, host):
        self.cli = "SMcli"
        self.host = host

    def run(self, arg):
        result = subprocess.run([self.cli, self.host, "-S", "-quick", "-c", arg], stdout=PIPE)
        return result.stdout
    
    def toJSON(self, dataframe):
        return dataframe.to_json(orient="records")
    
    def healthStatus(self):
        arg = 'show storagearray healthStatus;'
        result = "0"
        request = self.run(arg)
        if 'health status = optimal' in request.decode("utf-8"):
            result = "1"
        
        dataframe = pd.read_csv(filepath_or_buffer = io.StringIO(result),
                                names=['Status'])
        
        return self.toJSON(dataframe)
    
    def virtualDisks(self):
        arg = 'show virtualDisks;'
        request = self.run(arg)
        a = request.find(b'SUMMARY')
        b = request.find(b'DETAILS')
        request = request[a:b]
        raw = request.decode("utf-8")

        pattern = re.compile('([a-zA-Z0-9]\s+\w+\s+\w+\s+[a-zA-Z0-9.,]' +
                             '+\s\w+\s+Host\sGroup\s[a-zA-Z0-9_]' +
                             '+\s+Disk\sGroup\s[a-zA-Z0-9_]+)')

        table = ''
        for element in pattern.findall(raw):
            element = re.sub(r'(\s\s+)', ';', element, flags=re.UNICODE)
            element = re.sub(r'(^\(\';)', '', element, flags=re.UNICODE)
            element = re.sub(r'(\;\'\,\s+\'\\n\'\)$)', '', element, flags=re.UNICODE)
            table = table + element + "\n"

        dataframe = pd.read_csv(filepath_or_buffer = io.StringIO(table),
                                delimiter=';',
                                names=['Name',
                                       'Thin Provisioned',
                                       'Status',
                                       'Capacity',
                                       'Accessible by',
                                       'Source'])
        return self.toJSON(dataframe)

    def hwSummary(self):
        arg = 'show storageArray summary;'
        request = self.run(arg)
        a = request.find(b'HARDWARE SUMMARY')
        b = request.find(b'FEATURES SUMMARY')
        return request[a:b]

    def fwInventory(self):
        arg = 'show storageArray summary;'
        request = self.run(arg)
        a = request.find(b'FIRMWARE INVENTORY')
        b = request.find(b'SNMP SUMMARY')
        return request[a:b]

    def hardware(self):
        raw = self.hwSummary()
        a = raw.find(b'Physical Disks:')
        b = raw.find(b'Physical Disk security')
        pattern = re.compile('(\d+\s)')
        table = ''
        for element in pattern.findall((raw[a:b]).decode("utf-8")):
            table = table + element + ";"

        dataframe = pd.read_csv(filepath_or_buffer = io.StringIO(table[:-1]),
                                delimiter=';',
                                names=['Physical Disks',
                                       'Total hot spare physical disks',
                                       'Standby',
                                       'In use'])
        return self.toJSON(dataframe)
    
    def getPhysDisks(self):
        raw = self.fwInventory()
        raw = (raw[raw.find(b'Physical Disk'):]).decode("utf-8")
        pattern = re.compile('(Enclosure\s\d.*\n)')
        return pattern.findall(raw)
    
    def getPhysDisk(self, enclosure, slot):
        arg = "show physicalDisks [{0},{1}];".format(enclosure, slot)
        request = self.run(arg)
        a = request.find(b'Status')
        b = request.find(b'Raw capacity')
        raw = (request[a:b]).decode("utf-8")
        raw = raw.replace("Status:", "")
        raw = raw.replace("Mode:", "")
        pattern = re.compile('(\w+)')
        return pattern.findall(raw.strip())
    
    def physicalDisks(self):
        table = ''
        for element in self.getPhysDisks():
            disk = re.findall(r'(Enclosure\s)(\d)(\,\sSlot\s)(\d)', element, flags=re.UNICODE)
            status = self.getPhysDisk(disk[0][1], disk[0][3])
            element = element.replace("Enclosure ", "")
            element = element.replace(", Slot ", "   ")
            element = re.sub(r'(\s\s+)', ';', element, flags=re.UNICODE)
            table = table + element + status[0] + ";" + status[1] + "\n"

        dataframe = pd.read_csv(filepath_or_buffer = io.StringIO(table),
                                delimiter=';',
                                names=['Enclosure',
                                       'Slot',
                                       'Manufacturer',
                                       'Product ID',
                                       'Physical Disk Type',
                                       'Capacity',
                                       'Physical Disk firmware version',
                                       'FPGA Version',
                                       'Status',
                                       'Mode'])

        return self.toJSON(dataframe)

def call(obj, name):
    return getattr(obj, name)()

def main():
    md = PowerVaultMD(sys.argv[1])
    result =  call(md, sys.argv[2])
    js = json.loads(result)
    print(json.dumps(js, indent=4))

if __name__ == "__main__":
    main()
