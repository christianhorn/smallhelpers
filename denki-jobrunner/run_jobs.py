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

sutname     = "asahi"      # The system under test
hostrapl    = "asahi"          # What device will provide RAPL values?
hostbat     = "asahi"          # What device will provide battery values?
hosttasmota = "kosmos"      # What device will provide Tasmota values?

UseRapl     = False
UseBat      = True
UseTasmota  = False

oneline     = True          # Output machine readable one-line-results?

starttime   = ""
endtime     = ""

def ansiprep():
    ''' Prepare the sytem: install packages, deploy files '''
    command = "ansible-playbook -i ./inventory prepare_for_httpd.yml -l " + sutname
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
    command = "pminfo -h " + hostrapl + " -f denki.rapl | grep package-0"
    out = subprocess.check_output(command, shell=True)
    out2 = out.strip()
    out3 = re.sub('.* ', '', out2.decode('UTF-8'))
    return(int(out3))

def powerbat():
    ''' Read counter: What's the current battery charge? '''
    command = "pminfo -h " + hostrapl + " -f denki.bat.energy_now | grep battery-0"
    out = subprocess.check_output(command, shell=True)
    out2 = out.strip()
    out3 = re.sub('.* ', '', out2.decode('UTF-8'))
    return(float(out3.strip()))

def liverapl():
    ''' Read gauge: live value of currently consumed power according to RAPL '''
    command = "pmrep -h " + hostrapl + " denki.rapl -i package-0 -H -s2|tail -1"
    out = subprocess.check_output(command, shell=True)
    out2 = out.decode('UTF-8')
    out3 = out2.replace("\n","")
    return(out3.lstrip())

def runjob():
    raplconsumed,raplwatthourperrun,batconsumed,batwatthourperrun                       = 0,0,0,0
    TasConsumedOwn,TasConsumedRP,TasConsumedAP,TasConsumedP                             = 0,0,0,0
    TasWattHourperrunOwn,TasWattHourperrunRP,TasWattHourperrunAP,TasWattHourperrunP     = 0,0,0,0

    print("### Running ",job," for ",looptime,"sec..")
    if UseRapl == True:
        startrapl = powerrapl()
    if UseBat == True:
        startbat = powerbat()

    starttime = strftime("%H:%M:%S", localtime())
    starttimeepoc = int(time.time())

    command = "ssh -x chris@" + sutname + " \"cd /dev/shm; ./" + job + " " + str(looptime) + "\""
    print("\texecuting: ",command)
    out = subprocess.check_output(command, shell=True)
    endtime = strftime("%H:%M:%S", localtime())
    endtimeepoc = int(time.time())
    out2 = out.decode('UTF-8')
    # print(out2.lstrip())
    if UseRapl == True:
        endrapl = powerrapl()

    # Fetch: How many times did the job complete?
    command = "ssh -x -o'ControlMaster no' chris@" + sutname + " 'cat /tmp/counter'"
    out = subprocess.check_output(command, shell=True)
    out2 = out.decode('UTF-8')
    out3 = out2.replace("\n","")
    runs = out3.lstrip()

    # Fetch: How many threads were running in parallel?
    command = "ssh -x -o'ControlMaster no' chris@" + sutname + " 'cat /tmp/threads'"
    out = subprocess.check_output(command, shell=True)
    out2 = out.decode('UTF-8')
    out3 = out2.replace("\n","")
    threads = out3.lstrip()

    # How long did our job run?
    runtime = endtimeepoc - starttimeepoc

    # When the runtime is very small, we can finish not even a single run
    if int(runs) > 0:
        timeperjob = ( runtime * int(threads) ) / int(runs)
    else:
        timeperjob = 0

    print("\tWorkload did run",runs,"times, with ",threads," threads.")
    print("\tSingle jobs did run in average %.1f" % timeperjob,"sec.")

    if UseRapl == True:
        print("\t### RAPL")
        raplconsumed = ( endrapl - startrapl ) / runtime
        print("\t\tAverage power consumption: \t\t%.2f" % raplconsumed,"W")
        raplwatthourperrun = raplconsumed * timeperjob / 3600
        print("\t\tSingle job run, power consumption: \t%.5f" % raplwatthourperrun,"Wh")

    if UseBat == True:
        print("\t### Battery")
        endbat = powerbat()
        if endbat >= startbat:
            print("\t\tBattery did not discharge.. you need to run on battery for this method to work.")
        else:
            # print("\t\tBattery levels were ",startbat,"Wh at start, and ",endbat,"Wh at the end")
            batconsumed = ( startbat - endbat ) * ( 3600 / runtime )

            print("\t\tAverage power consumption: \t\t%.2f" % batconsumed,"W")
            batwatthourperrun = batconsumed * timeperjob / 3600
            print("\t\tSingle job run, power consumption: \t%.5f" % batwatthourperrun,"Wh")

    if UseTasmota == True:
        print("\t### Tasmota")

        tmp = subprocess.check_output("pcp|grep tasmota", shell=True)
        tmp2 = tmp.strip()
        archive = re.sub('.*: ', '', tmp2.decode('UTF-8'))
    
        # Tasmota power, own computed
        command = "pmrep -H -a " + archive + " -S @" + starttime + " -T @" + endtime + " openmetrics.tasmotalive4.Current openmetrics.tasmotalive4.Voltage"
        tmp = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).stdout
        lines = tmp.read().splitlines()
        # print("\t\tdebug: We got ",len(lines)," values to compute.")
        counter = 0.0
        validlines = 0
        for i in lines:
            # print("Line:",i)
            outright = re.sub('.* ', '', i.decode('UTF-8'))
            outlefttemp = re.sub('^ *', '', i.decode('UTF-8'))
            outleft = re.sub(' .*', '', outlefttemp)
            # print("debug left: ",float(outleft)," : right : ",float(outright))
            if outleft != 'N/A' and outright != 'N/A':
                counter += float(outleft) * float(outright)
                validlines += 1
        TasConsumedOwn = counter / validlines
        TasWattHourperrunOwn = TasConsumedOwn * timeperjob / 3600
        print("\t\tTasConsumedOwn: own calculated power consumption in average: \t\t%.2f" % TasConsumedOwn,"W")
        print("\t\t\tSingle job run, power consumption: \t%.5f" % TasWattHourperrunOwn,"Wh")

        # Tasmota power, ReactivePower
        command = "pmrep -H -a " + archive + " -S @" + starttime + " -T @" + endtime + " openmetrics.tasmotalive4.ReactivePower"
        tmp = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).stdout
        lines = tmp.read().splitlines()
        counter = 0.0
        validlines = 0
        for i in lines:
            # print("Line:",i)
            out = i.decode('UTF-8')
            if out != 'N/A':
                counter += float(out)
                validlines += 1
        TasConsumedRP = counter / validlines
        TasWattHourperrunRP = TasConsumedRP * timeperjob / 3600
        print("\t\tTasConsumedRP: own calculated power consumption in average: \t\t%.2f" % TasConsumedRP,"W")
        print("\t\t\tSingle job run, power consumption: \t%.5f" % TasWattHourperrunRP,"Wh")

        # Tasmota power, ApparentPower
        command = "pmrep -H -a " + archive + " -S @" + starttime + " -T @" + endtime + " openmetrics.tasmotalive4.ApparentPower"
        tmp = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).stdout
        lines = tmp.read().splitlines()
        counter = 0.0
        validlines = 0
        for i in lines:
            if i != 'N/A':
                # print("Line:",i)
                out = i.decode('UTF-8')
                counter += float(out)
                validlines += 1
        TasConsumedAP = counter / validlines
        TasWattHourperrunAP = TasConsumedAP * timeperjob / 3600
        print("\t\tTasConsumedAP: own calculated power consumption in average: \t\t%.2f" % TasConsumedAP,"W")
        print("\t\t\tSingle job run, power consumption: \t%.5f" % TasWattHourperrunAP,"Wh")

        # Tasmota power, Power
        command = "pmrep -H -a " + archive + " -S @" + starttime + " -T @" + endtime + " openmetrics.tasmotalive4.Power"
        tmp = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).stdout
        lines = tmp.read().splitlines()
        counter = 0.0
        validlines = 0
        for i in lines:
            if i != 'N/A':
                # print("Line:",i)
                out = i.decode('UTF-8')
                counter += float(out)
                validlines += 1
        TasConsumedP = counter / validlines
        TasWattHourperrunP = TasConsumedP * timeperjob / 3600
        print("\t\tTasConsumedP: own calculated power consumption in average: \t\t%.2f" % TasConsumedP,"W")
        print("\t\t\tSingle job run, power consumption: \t%.5f" % TasWattHourperrunP,"Wh")

    if oneline == True:
        print("\toneline",sutname,"%s" % job,"looptime-%s" % looptime,"runs-%s" % runs,"threads-%s" % threads,"timeperjob-%.1f" %timeperjob," ", end="")
        print("raplconsumption-%.2f" % raplconsumed,"raplwatthourperrun-%.5f" % raplwatthourperrun," ", end="")
        print("batconsumed-%.2f" % batconsumed,"batwatthourperrun-%.5f" % batwatthourperrun," ",end="")
        print("TasConsumed-%.2f-%.2f-%.2f-%.2f" % (TasConsumedOwn,TasConsumedRP,TasConsumedAP,TasConsumedP)," ",end="")
        print("TasWattHourperrun-%.5f-%.5f-%.5f-%.5f" % (TasWattHourperrunOwn,TasWattHourperrunRP,TasWattHourperrunAP,TasWattHourperrunP)," ",end="")
        print("")

# main

# fetch httpd:
# wget -O httpd-2.4.57.tar.bz2 http://archive.apache.org/dist/httpd/httpd-2.4.57.tar.bz2

ansiprep()
# if UseTasmota == True:
#     ansitasmotaprep()

looptime = 10
job = "job_sleep.sh"
runjob()
looptime = 30
job = "job_sleep.sh"
runjob()

job = "job_justload_full.sh"

looptime = 300
job = "job_httpd_extract_cpu.sh 1"
job = "job_httpd_extract_cpu.sh 2"
job = "job_httpd_extract_cpu.sh 3"
job = "job_httpd_extract_cpu.sh 4"
job = "job_httpd_extract_cpu.sh 5"
job = "job_httpd_extract_cpu.sh 6"
job = "job_httpd_extract_cpu.sh 7"
job = "job_httpd_extract_cpu.sh 8"
job = "job_httpd_extract_cpu.sh 10"
job = "job_httpd_extract_cpu.sh 12"
job = "job_httpd_extract_cpu.sh 14"
job = "job_httpd_extract_cpu.sh 13"
runjob()
#for i in range(20):
#    runjob()
