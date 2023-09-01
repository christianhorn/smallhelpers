#!/usr/bin/pmpython

# pylint: disable=bad-continuation,line-too-long,consider-using-dict-items
# pylint: disable=too-few-public-methods,too-many-nested-blocks

# GPLv2.0 or later
# Christian Horn <chorn@fluxcoil.net>

import time
from time import localtime, gmtime, strftime
import subprocess
import re
# import argparse
import sys
import os.path

host        = "steamdeck"      # The system under test
hostrapl    = "kosmos"          # What device will provide RAPL values?
hostbat     = "kosmos"          # What device will provide battery values?
hosttasmota = "kosmos"      # What device will provide Tasmota values?

userapl     = True
usebat      = False
usetasmota  = True

starttime   = ""
endtime     = ""

def ansiprep():
    ''' Prepare the sytem: install packages, deploy files '''
    command = "ansible-playbook -i ./inventory prepare_for_httpd.yml -l " + host
    print("### executing: ",command)
    out = subprocess.check_output(command, shell=True)
    out2 = out.decode('UTF-8')
    print("output:",out2)

def ansitasmotaprep():
    ''' Prepare the sytem for tasmota moniroting '''
    command = "ansible-playbook -i ./inventory prepare_tasmota_pmlogger.yml -l " + hosttasmota
    print("### executing: ",command)
    out = subprocess.check_output(command, shell=True)
    out2 = out.decode('UTF-8')
    print("output:",out2)

def powerrapl():
    ''' Read counter: What's the raw value for the rapl counter? '''
    command = "pmrep -h " + hostrapl + " denki.rapl.raw -i package-0 -H -s1"
    out = subprocess.check_output(command, shell=True)
    return(int(out))

def powerbat():
    ''' Read counter: What's the current battery charge? '''
    command = "pmrep -h " + hostbat + " denki.bat.energy_now_raw -H -s1"
    out = subprocess.check_output(command, shell=True)
    return(float(out.strip()))

def liverapl():
    ''' Read gauge: live value of currently consumed power according to RAPL '''
    command = "pmrep -h " + hostrapl + " denki.rapl.rate -i package-0 -H -s2|tail -1"
    out = subprocess.check_output(command, shell=True)
    out2 = out.decode('UTF-8')
    out3 = out2.replace("\n","")
    return(out3.lstrip())

def runjob():
    print("### Running ",job," for at least ",looptime,"sec..")
    if userapl == True:
        startrapl = powerrapl()
    if usebat == True:
        startbat = powerbat()

    starttime = strftime("%H:%M:%S", localtime())
    starttimeepoc = int(time.time())

    command = "ssh -x chris@" + host + " \"cd /dev/shm; ./" + job + " " + str(looptime) + "\""
    print("\texecuting: ",command)
    out = subprocess.check_output(command, shell=True)
    endtime = strftime("%H:%M:%S", localtime())
    endtimeepoc = int(time.time())
    out2 = out.decode('UTF-8')
    # print(out2.lstrip())
    if userapl == True:
        endrapl = powerrapl()

    command = "ssh -x -o'ControlMaster no' chris@" + host + " 'cat /tmp/counter'"
    out = subprocess.check_output(command, shell=True)
    out2 = out.decode('UTF-8')
    out3 = out2.replace("\n","")
    runs = out3.lstrip()

    runtime = endtimeepoc - starttimeepoc

    timestep = 3600 / runtime
    runsperhour = runtime * timestep
    timeperjob = runtime / int(runs)

    print("\tWorkload did run",runs,"times, a single job did run %.1f" % timeperjob,"sec.")
    # print("\tStarttime:",starttime," endtime: ",endtime)
    

    if userapl == True:
        print("\t### RAPL")
        consumed = ( endrapl - startrapl ) / runtime
        print("\t\tAverage power consumption: \t\t%.2f" % consumed,"W")
        watthourperrun = consumed * timeperjob / 3600
        print("\t\tSingle job run, power consumption: \t%.5f" % watthourperrun,"Wh")

    if usebat == True:
        print("\t### Battery")
        endbat = powerbat()
        if endbat >= startbat:
            print("\t\tBattery did not discharge.. you need to run on battery for this method to work.")
        else:
            # print("\t\tBattery levels were ",startbat,"Wh at start, and ",endbat,"Wh at the end")
            consumed = ( startbat - endbat ) * timestep
            print("\t\tAverage power consumption: \t\t%.2f" % consumed,"W")
            watthourperrun = consumed * timeperjob / 3600
            print("\t\tSingle job run, power consumption: \t%.5f" % watthourperrun,"Wh")

    if usetasmota == True:
        print("\t### Tasmota")

        tmp = subprocess.check_output("pcp|grep tasmota", shell=True)
        tmp2 = tmp.strip()
        archive = re.sub('.*: ', '', tmp2.decode('UTF-8'))
    
        # dummy data:
        # command = "pmrep -a /var/log/pcp/pmlogger/tasmota/20230821 -S @21:03:00 -T @21:06:13 :tasmota2"
        # real data:
        command = "pmrep -a " + archive + " -S @" + starttime + " -T @" + endtime + " :tasmota2"
        # print("\t\tdebug: command",command)
        tmp = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).stdout
        lines = tmp.read().splitlines()
        # print("\t\tdebug: We got ",len(lines)," values to compute.")
        counter = 0.0
        for i in lines:
            if i != 'N/A':
                counter += float(i)
        consumed = counter / len(lines)
    
        print("\t\tAverage power consumption: \t\t%.2f" % consumed,"W")
        watthourperrun = consumed * timeperjob / 3600
        print("\t\tSingle job run, power consumption: \t%.5f" % watthourperrun,"Wh")


# main

# ansiprep()
# if usetasmota == True:
#    ansitasmotaprep()

looptime = 100
job = "job_sleep.sh"
runjob()

looptime = 300
job = "job_justload_4.sh"
runjob()

looptime = 300
job = "job_httpd_extract.sh"
runjob()

looptime = 300
job = "job_httpd_compile.sh"
runjob()
