#!/usr/bin/pmpython

# pylint: disable=bad-continuation,line-too-long,consider-using-dict-items
# pylint: disable=too-few-public-methods,too-many-nested-blocks

# GPLv2.0 or later
# Christian Horn <chorn@fluxcoil.net>

import time
from time import localtime, gmtime, strftime
from pathlib import Path
import subprocess
import re
import sys
import os.path

sutname     = "amd64"      # The system under test
hostrapl    = "kosmos"      # Which system will provide RAPL values?
hostbat     = "asahi"       # Which system will provide battery values?
hosttasmota = "kosmos"      # Which system will provide Tasmota values?
hostlmsensors = "asahi"     # Which system will provide lmsensors values?

UseRaplSysfs    = False      # Use RAPL filesystem metrics (x86 only)
UseRaplMSR      = True      # Use RAPL MSR register metrics (x86 only, select Intel CPUs)
UseBat          = False
UseTasmota      = False
UseAsahiPower   = False     # Use MAC/Asahi power metric, available also when plugged in

oneline     = True          # Output machine readable one-line-results?

starttime   = ""
endtime     = ""

# Global variables for various metering methods: consumed port, and power per run
RaplSysfsConsumed,RaplSysfsWatthourperrun       = 0,0
RaplMsrConsumed,RaplMsrWatthourperrun           = 0,0
BatConsumed,BatWatthourperrun                   = 0,0
TasConsumedP,TasWattHourperrunP                 = 0,0
AsahiConsumedP,AsahiWattHourperrunP             = 0,0

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

def ansilmsensorsprep():
    ''' Prepare the sytem for lmsensors moniroting '''
    command = "ansible-playbook -i ./inventory prepare_lmsensors_pmlogger.yml -l " + hostlmsensors
    print("### executing: ",command)
    out = subprocess.check_output(command, shell=True)
    out2 = out.decode('UTF-8')
    print("output:",out2)

def powerraplsysfs():
    ''' Read counter: What's the raw value for the rapl sysfs counter? '''
    command = "pminfo -h " + hostrapl + " -f denki.rapl.sysfs | grep package-0"
    out = subprocess.check_output(command, shell=True)
    out2 = out.strip()
    out3 = re.sub('.* ', '', out2.decode('UTF-8'))
    return(int(out3))

def powerraplmsr():
    ''' Read counter: What's the raw value for the rapl MSR counter? '''
    # command = "pminfo -h " + hostrapl + " -f denki.rapl.msr | grep psys_energy"
    command = "pminfo -h " + hostrapl + " -f denki.rapl.msr | grep package_energy"
    out = subprocess.check_output(command, shell=True)
    out2 = out.strip()
    out3 = re.sub('.* ', '', out2.decode('UTF-8'))
    return(int(out3))

def powerbat():
    ''' Read counter: What's the current battery charge? '''
    command = "pminfo -h " + hostbat + " -f denki.bat.energy_now | grep battery-0"
    out = subprocess.check_output(command, shell=True)
    out2 = out.strip()
    out3 = re.sub('.* ', '', out2.decode('UTF-8'))
    return(float(out3.strip()))


def calculateAsahiPower():
    global starttime
    global endtime
    global runs
    global runtime
    global AsahiConsumedP,AsahiWattHourperrunP
    print("    ### AsahiPower method")

    tmp = subprocess.check_output("pcp|grep -E 'logger.*lmsensors'", shell=True)
    tmp2 = tmp.strip()
    archive = re.sub('.*: ', '', tmp2.decode('UTF-8'))

    # Actual calculation
    command = "pmrep -H -t 5s -a " + archive + " -S @" + starttime + " -T @" + endtime + " lmsensors.macsmc_hwmon_isa_0000.total_system_power"
    # print("debug command:",command)
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
    AsahiConsumedP = counter / validlines
    AsahiWattHourperrunP = AsahiConsumedP / ( 3600 * int(runs) / runtime )
    print("        AsahiConsumedP: own calculated power consumption in average:         %.2f" % AsahiConsumedP,"W")
    print("            Single job run, power consumption:     %.5f" % AsahiWattHourperrunP,"Wh")


def calculateTasmota():
    global starttime
    global endtime
    global runs
    global runtime
    print("    ### Tasmota")

    tmp = subprocess.check_output("pcp|grep tasmota", shell=True)
    tmp2 = tmp.strip()
    archive = re.sub('.*: ', '', tmp2.decode('UTF-8'))

    # Tasmota power, own computed
    command = "pmrep -H -a " + archive + " -S @" + starttime + " -T @" + endtime + " openmetrics.tasmotalive4.Current openmetrics.tasmotalive4.Voltage"
    tmp = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).stdout
    lines = tmp.read().splitlines()
    # print("        debug: We got ",len(lines)," values to compute.")
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
    TasWattHourperrunOwn = TasConsumedOwn / ( 3600 * int(runs) / runtime )
    print("        TasConsumedOwn: own calculated power consumption in average:         %.2f" % TasConsumedOwn,"W")
    print("            Single job run, power consumption:     %.5f" % TasWattHourperrunOwn,"Wh")

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
    TasWattHourperrunRP = TasConsumedRP / ( 3600 * int(runs) / runtime )
    print("        TasConsumedRP: own calculated power consumption in average:         %.2f" % TasConsumedRP,"W")
    print("            Single job run, power consumption:     %.5f" % TasWattHourperrunRP,"Wh")

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
    TasWattHourperrunAP = TasConsumedAP / ( 3600 * int(runs) / runtime )
    print("        TasConsumedAP: own calculated power consumption in average:         %.2f" % TasConsumedAP,"W")
    print("            Single job run, power consumption:     %.5f" % TasWattHourperrunAP,"Wh")

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
    TasWattHourperrunP = TasConsumedP / ( 3600 * int(runs) / runtime )
    print("        TasConsumedP: own calculated power consumption in average:         %.2f" % TasConsumedP,"W")
    print("            Single job run, power consumption:     %.5f" % TasWattHourperrunP,"Wh")

def runjobplain():
    global starttime
    global endtime
    global runs
    global runtime
    global RaplSysfsConsumed,RaplSysfsWatthourperrun
    global RaplMsrConsumed,RaplMsrWatthourperrun,BatConsumed,BatWatthourperrun
    global TasConsumedP,TasWattHourperrunP
    global AsahiConsumedP,AsahiWattHourperrunP

    print("### Running ",job," for ",looptime,"sec..")
    if UseRaplSysfs == True:
        startraplsysfs = powerraplsysfs()
    if UseRaplMSR == True:
        startraplmsr = powerraplmsr()
    if UseBat == True:
        startbat = powerbat()

    starttime = strftime("%H:%M:%S", localtime())
    starttimeepoc = int(time.time())

    command = "ssh -x chris@" + sutname + " \"cd /dev/shm; bash ./" + job + " " + str(looptime) + "\""
    print("    executing:",command)
    out = subprocess.check_output(command, shell=True)
    endtime = strftime("%H:%M:%S", localtime())
    endtimeepoc = int(time.time())
    out2 = out.decode('UTF-8')
    # print(out2.lstrip())

    if UseRaplSysfs == True:
        endraplsysfs = powerraplsysfs()
    if UseRaplMSR == True:
        endraplmsr = powerraplmsr()

    # Fetch results
    command = "ssh -x -o'ControlMaster no' chris@" + sutname + " 'cat /tmp/results'"
    out = subprocess.check_output(command, shell=True)
    out2 = out.decode('UTF-8')
    out3 = out2.replace("\n","")
    results = out3.lstrip()

    # How long did our job run, wallclock time?
    runtime = endtimeepoc - starttimeepoc

    print("    Workload results:", results)

    if UseRaplSysfs == True:
        print("    ### RAPL Filesystem")
        RaplSysfsConsumed = ( endraplsysfs - startraplsysfs ) / runtime
        print("        Average power consumption:         %.2f" % RaplSysfsConsumed,"W")

    if UseRaplMSR == True:
        print("    ### RAPL MSR")
        RaplMsrConsumed = ( endraplmsr - startraplmsr ) / runtime
        print("        Average power consumption:         %.2f" % RaplMsrConsumed,"W")

    if UseBat == True:
        print("    ### Battery")
        endbat = powerbat()
        if endbat >= startbat:
            print("        Battery did not discharge.. you need to run on battery for this method to work.")
        else:
            BatConsumed = ( startbat - endbat ) * ( 3600 / runtime )
            print("        Average power consumption:         %.2f" % BatConsumed,"W")

    if UseTasmota == True:
        calculateTasmota()

    if UseAsahiPower == True:
        calculateAsahiPower()

    if oneline == True:
        print("    oneline",sutname,"%s" % job,"looptime-%s" % looptime,"results-%s" % results, "",end="")
        if UseRaplSysfs == True:
            print("RaplSysFS-%.2f" % RaplSysfsConsumed,"", end="")
        if UseRaplMSR == True:
            print("RaplMSR-%.2f" % RaplMsrConsumed,"", end="")
        if UseBat == True:
            print("Bat-%.2f" % BatConsumed,"",end="")
        if UseTasmota == True:
            print("Tasmota-%.2f" % TasConsumedP,"",end="")
        if UseAsahiPower == True:
            print("Asahi-%.2f" % AsahiConsumedP,"",end="")
        print("")

def runjobthreaded():
    global starttime
    global endtime
    global runs
    global runtime
    global RaplSysfsConsumed,RaplSysfsWatthourperrun
    global RaplMsrConsumed,RaplMsrWatthourperrun,BatConsumed,BatWatthourperrun
    global TasConsumedP,TasWattHourperrunP
    global AsahiConsumedP,AsahiWattHourperrunP

    print("### Running ",job," for ",looptime,"sec..")
    if UseRaplSysfs == True:
        startraplsysfs = powerraplsysfs()
    if UseRaplMSR == True:
        startraplmsr = powerraplmsr()
    if UseBat == True:
        startbat = powerbat()

    starttime = strftime("%H:%M:%S", localtime())
    starttimeepoc = int(time.time())

    command = "ssh -x chris@" + sutname + " \"cd /dev/shm; bash ./" + job + " " + str(looptime) + "\""
    print("    executing:",command)
    out = subprocess.check_output(command, shell=True)
    endtime = strftime("%H:%M:%S", localtime())
    endtimeepoc = int(time.time())
    out2 = out.decode('UTF-8')
    # print(out2.lstrip())

    if UseRaplSysfs == True:
        endraplsysfs = powerraplsysfs()
    if UseRaplMSR == True:
        endraplmsr = powerraplmsr()

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

    if runtime == 0.0:
        runtime = 0.1

    print("    Workload did run",runs,"times, with ",threads," threads.")
    print("    Single jobs did run in average %.1f" % timeperjob,"sec.")

    if UseRaplSysfs == True:
        print("    ### RAPL Filesystem")
        RaplSysfsConsumed = ( endraplsysfs - startraplsysfs ) / runtime
        print("        Average power consumption:         %.2f" % RaplSysfsConsumed,"W")
        RaplSysfsWatthourperrun = RaplSysfsConsumed / ( 3600 * int(runs) / runtime )
        print("        Single job run, power consumption:     %.5f" % RaplSysfsWatthourperrun,"Wh")

    if UseRaplMSR == True:
        print("    ### RAPL MSR")
        RaplMsrConsumed = ( endraplmsr - startraplmsr ) / runtime
        print("        Average power consumption:         %.2f" % RaplMsrConsumed,"W")
        RaplMsrWatthourperrun = RaplMsrConsumed / ( 3600 * int(runs) / runtime )
        print("        Single job run, power consumption:     %.5f" % RaplMsrWatthourperrun,"Wh")

    if UseBat == True:
        print("    ### Battery")
        endbat = powerbat()
        if endbat >= startbat:
            print("        Battery did not discharge.. you need to run on battery for this method to work.")
        else:
            # print("        Battery levels were ",startbat,"Wh at start, and ",endbat,"Wh at the end")
            BatConsumed = ( startbat - endbat ) * ( 3600 / runtime )

            print("        Average power consumption:         %.2f" % BatConsumed,"W")
            BatWatthourperrun = BatConsumed / ( 3600 * int(runs) / runtime )
            print("        Single job run, power consumption:     %.5f" % BatWatthourperrun,"Wh")

    if UseTasmota == True:
        calculateTasmota()

    if UseAsahiPower == True:
        calculateAsahiPower()

    if oneline == True:
        print("    oneline",sutname,"%s" % job,"looptime-%s" % looptime,"runs-%s" % runs,"threads-%s" % threads,"timeperjob-%.1f" %timeperjob,"", end="")
        if UseRaplSysfs == True:
            print("RaplSysFS-%.2f-%.5f" % (RaplSysfsConsumed,RaplSysfsWatthourperrun),"", end="")
        if UseRaplMSR == True:
            print("RaplMSR-%.2f-%.5f" % (RaplMsrConsumed,RaplMsrWatthourperrun),"", end="")
        if UseBat == True:
            print("Bat-%.2f-%.5f" % (BatConsumed,BatWatthourperrun),"",end="")
        if UseTasmota == True:
            print("Tasmota-%.2f-%.5f" % (TasConsumedP,TasWattHourperrunP),"",end="")
        if UseAsahiPower == True:
            print("Asahi-%.2f-%.5f" % (AsahiConsumedP,AsahiWattHourperrunP),"",end="")
        print("")

# main

# fetch httpd:
# wget -O httpd-2.4.57.tar.bz2 http://archive.apache.org/dist/httpd/httpd-2.4.57.tar.bz2

print("CUSTOM: reports package consumption instead of phys.")
# Do we need to fetch httpd?
httpdfile = Path('./files/httpd-2.4.57.tar.bz2')
if not httpdfile.is_file():
    print("files/httpd-2.4.57.tar.bz2 not found, fetching..")
    command = "wget -nv -O files/httpd-2.4.57.tar.bz2 http://archive.apache.org/dist/httpd/httpd-2.4.57.tar.bz2"
    out = subprocess.check_output(command, shell=True)
    out2 = out.decode('UTF-8')
    print("done.",out2)

# ansiprep()

if UseTasmota == True:
    ansitasmotaprep()
if UseAsahiPower == True:
    # TODO: pmlogger conf file needs customization to actual systems hostname
    ansilmsensorsprep()

looptime = 10
job = "job_sleep.sh"
runjobthreaded()
looptime = 300

job = "job_justload_full.sh"
# runjobthreaded()


job = "job_io_read.sh"
runjobplain()
job = "job_io_write_nosync.sh"
runjobplain()
job = "job_io_write_sync.sh"
runjobplain()


job = "job_memwrite-128m-nosync.sh"
#runjobplain()
job = "job_memwrite-128m-sync.sh"
#runjobplain()
job = "job_memwrite-1024m-nosync.sh"
runjobplain()
job = "job_memwrite-1024m-sync.sh"
runjobplain()


job = "job_iperf3_4.1.sh"
# job = "job_iperf_4.1.sh"
#runjobplain()


job = "job_httpd_extract_cpu.sh 1"
runjobthreaded()
job = "job_httpd_extract_cpu.sh 2"
runjobthreaded()
job = "job_httpd_extract_cpu.sh 3"
job = "job_httpd_extract_cpu.sh 4"
runjobthreaded()
job = "job_httpd_extract_cpu.sh 5"
job = "job_httpd_extract_cpu.sh 6"
job = "job_httpd_extract_cpu.sh 7"
job = "job_httpd_extract_cpu.sh 8"
runjobthreaded()
job = "job_httpd_extract_cpu.sh 10"
job = "job_httpd_extract_cpu.sh 14"
job = "job_httpd_extract_cpu.sh 12"
job = "job_httpd_extract_cpu.sh 13"
#for i in range(20):
#    runjob()
