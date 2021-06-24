#!/usr/bin/env python3
# coding: utf-8

import io
import sys
import re
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
    
    def healthStatus(self):
        arg = 'show storagearray healthStatus;'
        result = "0"
        request = self.run(arg)
        if 'health status = optimal' in request:
            result = "1"
        return result
    
    def virtualDisks(self):
        arg = 'show virtualDisks;'
        request = self.run(arg)
        a = request.find(b'SUMMARY')
        b = request.find(b'DETAILS')
        request = request[a:b]
        raw = request.decode("utf-8")

        pattern = re.compile('([a-z0-9]\s+\w+\s+\w+\s+[a-z0-9.,]' +
                             '+\s\w+\s+Host\sGroup\s[a-z0-9_]' +
                             '+\s+Disk\sGroup\s[a-z0-9_]+)')

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
        return dataframe

    
def call(obj, name):
    return getattr(obj, name)()

def main():
    md = PowerVaultMD(sys.argv[1])
    dataframe =  call(md, sys.argv[2])
    print(dataframe)

if __name__ == "__main__":
    main()
